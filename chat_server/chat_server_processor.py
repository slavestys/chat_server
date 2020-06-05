from aiohttp import web
from typing import List
import datetime
from typing import Union
import tortoise

from models import User, Message, Room, UserRoom
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
        self.__state = self.STATE_AUTHENTICATED
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
            rooms_client_data.append({'id': room.id, 'name': room.name, 'messages': messages_client_data})
        users = await User.filter(id__in=users_to_search).all()
        users_data = [user.chat_client_data() for user in users]
        await self.__chat_state.online(self)
        await self.send_message(protocol.AuthSuccess.make(self, self.__user, rooms_client_data, users_data, cmd_id=cmd_id).serialize())

    async def process_auth(self, command: protocol.Auth):
        self.__user = await User.filter(name=command.login(), passwd=command.passwd()).first()
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

    async def process_chat_message(self, command: protocol.Message):
        room_id = command.room_id
        if room_id not in self.__user_rooms:
            await self.on_error(protocol.Error.ERR_USER_NOT_IN_ROOM, cmd_id=command.cmd_id)
            return
        msg = command.message
        if not msg:
            await self.on_error(protocol.Error.ERR_MESSAGE_EMPTY, cmd_id=command.cmd_id)
            return
        message = await Message.create(room_id=room_id, message=msg, user_id=self.__user.id, created_at=datetime.datetime.now())
        await self.__chat_state.send_message(message, self)
        await self.send_success(command.cmd_id, data=message.client_data())

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
        await self.__chat_state.send_message_edited(message, self, message.room_id)
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
            room = await Room.create(name=room_name)
            await self.__user.rooms.add(room)
            await self._on_join_to_room(room.id)
            await self.send_success(command.cmd_id, room_id=room.id)

    async def on_error(self, error_code: int, error_message: Union[str, Exception] = None, cmd_id: int = None):
        return await self.send_message(protocol.Error.make(self, error_code, error_message=error_message, cmd_id=cmd_id).serialize())

    def send_success(self, cmd_id: int, **parameters):
        return self.send_message(protocol.CommandSuccess.make(self, cmd_id=cmd_id, **parameters).serialize())

    @property
    def room_ids(self):
        return self.__user_rooms

    @property
    def user_id(self) -> int:
        return self.__user.id

    @property
    def user_name(self) -> str:
        return self.__user.name

    def authenticated(self):
        return self.__user is not None

    def _on_join_to_room(self, room_id):
        self.__user_rooms.append(room_id)
        return self.__chat_state.join_to_rooms(self, room_id)


