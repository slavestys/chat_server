from aiohttp import web
from typing import List
import datetime
from typing import Union
import tortoise
from tortoise.query_utils import Q

from models import User, Message, Room, UserRoom, Contact
from chat_common import protocol
from chat_common import ChatProcessorBase


class ChatServerProcessor(ChatProcessorBase):
    __user: User = None
    __user_rooms: List[int]

    def __init__(self, websocket: web.WebSocketResponse, chat_state):
        super(ChatServerProcessor, self).__init__(websocket)
        self.__user_rooms = []
        self.__chat_state = chat_state

    async def _finish_session(self):
        await self.__chat_state.offline(self)

    async def __process_auth_success(self, cmd_id):
        self._state = self.STATE_AUTHENTICATED
        rooms = await self.__user.rooms.all()
        self.__user_rooms = [room.id for room in rooms]
        rooms_client_data = []
        users_to_search = set(await UserRoom.filter(room_id__in=self.__user_rooms).values_list("user_id", flat=True))
        for room in rooms:
            messages_client_data = []
            messages = await room.messages.all()
            for message in messages:
                messages_client_data.append(message.client_data())
                users_to_search.add(message.user_id)
            rooms_client_data.append(room.client_data(messages_client_data))
        contacts = await Contact.find_contacts(self.user_id)
        contacts_data = []
        for contact in contacts:
            users_to_search.add(contact.user1_id)
            users_to_search.add(contact.user2_id)
            contacts_data.append(contact.client_data(self.user_id))
        users = await User.filter(id__in=users_to_search).all()
        users_data = [user.chat_client_data() for user in users]
        await self.__chat_state.online(self)
        await self.send_message(
            protocol.AuthSuccess.make(
                self,
                user_client_data=self.__user.chat_client_data(),
                rooms_client_data=rooms_client_data,
                users=users_data,
                contacts=contacts_data,
                cmd_id=cmd_id
            ).serialize()
        )

    async def process_auth(self, command: protocol.Auth):
        self.__user = await User.filter(login=command.login(), passwd=command.passwd()).first()
        if self.__user:
            await self.__process_auth_success(command.cmd_id)
        else:
            await self.on_error(protocol.Error.ERR_AUTH_FAILED, cmd_id=command.cmd_id)

    async def process_auth_by_key(self, command: protocol.AuthByKey):
        self.__user = await User.filter(id=command.user_id()).first()
        if self.__user and self.__user.key() == command.key():
            await self.__process_auth_success(command.cmd_id)
        else:
            await self.on_error(protocol.Error.ERR_AUTH_FAILED, cmd_id=command.cmd_id)

    async def process_chat_message(self, command: protocol.MessageCreate):
        room_id = command.room_id
        if room_id not in self.__user_rooms:
            await self.on_error(protocol.Error.ERR_USER_NOT_IN_ROOM, cmd_id=command.cmd_id)
            return
        msg = command.message
        if not msg:
            await self.on_error(protocol.Error.ERR_MESSAGE_EMPTY, cmd_id=command.cmd_id)
            return
        message = await Message.create(room_id=room_id, message=msg, user_id=self.__user.id, created_at=datetime.datetime.now())
        await self._on_message_saved(message, command.cmd_id)

    async def process_chat_message_edit(self, command: protocol.MessageEdit):
        message_id = command.message_id
        message = await Message.filter(id=message_id).get_or_none()
        if not message:
            await self.on_error(protocol.Error.ERR_MESSAGE_NOT_FOUND, cmd_id=command.cmd_id)
            return
        if message.user_id != self.__user.id:
            await self.on_error(protocol.Error.ERR_CAN_T_EDIT_MESSAGE, cmd_id=command.cmd_id)
            return
        message.message = command.message
        await message.save()
        await self.__chat_state.send_message_edited(message, self)
        await self.send_success(command.cmd_id)

    async def process_room_join(self, command: protocol.RoomJoin):
        room_id = command.room_id
        if not room_id:
            await self.on_error(protocol.Error.ERR_ROOM_ID_REQUIRED, cmd_id=command.cmd_id)
            return
        if room_id in self.__user_rooms:
            await self.on_error(protocol.Error.ERR_ALREADY_IN_ROOM, cmd_id=command.cmd_id)
            return
        room = await Room.get_or_none(id=room_id)
        if not room:
            await self.on_error(protocol.Error.ERR_ROOM_NOT_FOUND, cmd_id=command.cmd_id)
            return
        await self.__user.rooms.add(room)
        await self._on_join_to_room(room_id)
        await self.send_success(command.cmd_id)

    async def process_room_leave(self, command: protocol.RoomLeave):
        room_id = command.room_id
        if room_id not in self.__user_rooms:
            await self.on_error(protocol.Error.ERR_USER_NOT_IN_ROOM, cmd_id=command.cmd_id)
            return
        await self.__user.rooms.remove(Room(id=room_id))
        self.__user_rooms.remove(room_id)
        await self.__chat_state.leave_from_rooms(self, room_id)
        await self.send_success(command.cmd_id)

    async def process_room_create(self, command: protocol.RoomCreate):
        room_name = command.name
        async with tortoise.transactions.in_transaction():
            room = await Room.create(name=room_name, room_type=protocol.Room.TYPE_CHAT)
            await self.__user.rooms.add(room)
            await self._on_join_to_room(room.id)
            await self.send_success(command.cmd_id, room_id=room.id)

    async def process_contact_add(self, command: protocol.ContactAdd):
        user_id = command.user_id
        user = await User.filter(id=user_id).get_or_none()
        if not user:
            await self.on_error(protocol.Error.ERR_USER_NOT_FOUND, cmd_id=command.cmd_id)
            return
        contact = await Contact.find_contact(user1_id=self.user_id, user2_id=user_id)
        if contact and contact.contact_enabled:
            await self.on_error(protocol.Error.ERR_CONTACT_EXISTS, cmd_id=command.cmd_id)
            return
        async with tortoise.transactions.in_transaction():
            if contact:
                contact.contact_enabled = True
                await contact.save()
            else:
                contact = await Contact.create(user1_id=self.user_id, user2_id=user_id)
            room_name = str(contact.id)
            room = await Room.filter(name=room_name, room_type=protocol.Room.TYPE_USER).get_or_none()
            if room:
                room.room_enabled = True
                await room.save()
            else:
                room = await Room.create(name=room_name, room_type=protocol.Room.TYPE_USER)
                await self.__user.rooms.add(room)
                await UserRoom.create(user_id=user_id, room_id=room.id)
        await self.__chat_state.added_contact(self, receiver_id=self.user_id, contact_id=contact.id, user=user, room=room)
        await self.__chat_state.added_contact(self, receiver_id=user_id, contact_id=contact.id, user=self.user, room=room)
        await self.send_success(command.cmd_id, contact_id=contact.id, user=user.chat_client_data(), room=room.client_data())

    async def process_contact_remove(self, command: protocol.ContactRemove):
        user_id = command.user_id
        user = await User.filter(id=user_id).get_or_none()
        if not user:
            await self.on_error(protocol.Error.ERR_USER_NOT_FOUND, cmd_id=command.cmd_id)
            return
        contact = await Contact.find_contact(user1_id=self.user_id, user2_id=user_id)
        if not contact or not contact.contact_enabled:
            await self.on_error(protocol.Error.ERR_CONTACT_NOT_EXISTS, cmd_id=command.cmd_id)
            return
        async with tortoise.transactions.in_transaction():
            room_name = str(contact.id)
            contact.contact_enabled = False
            await contact.save()
            room = await Room.filter(name=room_name, room_type=protocol.Room.TYPE_USER).get_or_none()
            if room:
                room.room_enabled = False
                await room.save()
        await self.__chat_state.removed_contact(self, receiver_id=self.user_id, contact_id=contact.id, room_id=room.id)
        await self.__chat_state.removed_contact(self, receiver_id=user_id, contact_id=contact.id, room_id=room.id)
        await self.send_success(command.cmd_id, contact_id=contact.id, room_id=room.id)

    async def process_search_users(self, command: protocol.UsersSearch):
        name = command.name
        users = await User.filter(Q(name__icontains=name, login__icontains=name, join_type='OR')).all()
        user_data = [user.chat_client_data() for user in users]
        await self.send_success(command.cmd_id, users=user_data)

    async def on_error(self, error_code: int, error_message: Union[str, Exception] = None, cmd_id: int = None):
        return await self.send_message(protocol.Error.make(self, error_code, error_message=error_message, cmd_id=cmd_id).serialize())

    def send_success(self, cmd_id: int, **parameters):
        return self.send_message(protocol.CommandSuccess.make(self, cmd_id=cmd_id, **parameters).serialize())

    def add_to_room(self, room_id: int):
        if room_id in self.__user_rooms:
            return False
        self.__user_rooms.append(room_id)
        return True

    @property
    def room_ids(self):
        return self.__user_rooms

    @property
    def user(self) -> User:
        return self.__user

    @property
    def user_id(self) -> int:
        return self.__user.id

    @property
    def user_name(self) -> str:
        return self.__user.name

    def authenticated(self):
        return self.__user is not None

    def _on_join_to_room(self, room_id):
        return self.__chat_state.join_to_rooms(self, room_id)

    async def _on_message_saved(self, message: Message, cmd_id: int):
        await self.__chat_state.send_message(message, self)
        await self.send_success(cmd_id, data=message.client_data())



