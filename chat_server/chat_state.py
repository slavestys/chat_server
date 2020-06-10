from typing import List, Dict, Set
import json
import asyncio

from .chat_server_processor import ChatServerProcessor
from chat_common.protocol import SystemMessage, Message, MessageEdit, MessageInfo
import models


class ChatState:
    __clients: Dict[int, List[ChatServerProcessor]]
    __room_clients: Dict[int, List[ChatServerProcessor]]
    __unauthorized: List[ChatServerProcessor]

    def __init__(self):
        self.__clients = {}
        self.__room_clients = {}
        self.__unauthorized = []

    def all_chat_users(self, sender: ChatServerProcessor, *room_ids: int) -> Set[ChatServerProcessor]:
        chat_users = set()
        for room_id in room_ids:
            room_processors = self.__room_clients.get(room_id)
            if not room_processors:
                continue
            for chat_server_processor in room_processors:
                if chat_server_processor == sender:
                    continue
                chat_users.add(chat_server_processor)
        return chat_users

    def add_user(self, chat_server_processor: ChatServerProcessor):
        self.__unauthorized.append(chat_server_processor)

    def add_authorized(self, chat_server_processor: ChatServerProcessor):
        self.__unauthorized.remove(chat_server_processor)
        user_id = chat_server_processor.user_id
        user_processors = self.__clients.get(user_id)
        if not user_processors:
            user_processors = self.__clients[user_id] = []
        user_processors.append(chat_server_processor)

    def remove_user(self, chat_server_processor: ChatServerProcessor):
        if not chat_server_processor.authenticated():
            self.__unauthorized.remove(chat_server_processor)
            return
        user_id = chat_server_processor.user_id
        user_processors = self.__clients.get(user_id)
        if not user_processors:
            return
        user_processors.remove(chat_server_processor)
        if not user_processors:
            del self.__clients[user_id]

    async def online(self, sender: ChatServerProcessor):
        self.add_authorized(sender)
        self.add_to_rooms(sender, *sender.room_ids)
        message = SystemMessage.make(sender, SystemMessage.USER_ONLINE, user_id=sender.user_id, user_name=sender.user_name).serialize()
        awaitables = [chat_server_processor.send_message(message) for chat_server_processor in self.all_chat_users(sender, *sender.room_ids)]
        if not awaitables:
            return
        await asyncio.wait(awaitables)

    async def offline(self, sender: ChatServerProcessor):
        self.remove_user(sender)
        if not sender.authenticated():
            return
        self.remove_from_rooms(sender, *sender.room_ids)
        message = SystemMessage.make(sender, SystemMessage.USER_OFFLINE, user_id=sender.user_id, user_name=sender.user_name).serialize()
        awaitables = [chat_server_processor.send_message(message) for chat_server_processor in self.all_chat_users(sender, *sender.room_ids)]
        if not awaitables:
            return
        await asyncio.wait(awaitables)

    async def join_to_rooms(self, sender: ChatServerProcessor, *room_ids: int):
        self.add_to_rooms(sender, *room_ids)
        for room_id in room_ids:
            message = SystemMessage.make(sender, SystemMessage.USER_JOINED, user_id=sender.user_id, room_id=room_id, user_name=sender.user_name).serialize()
            awaitables = [chat_server_processor.send_message(message) for chat_server_processor in self.__room_clients[room_id] if chat_server_processor != sender]
            if not awaitables:
                return
            await asyncio.wait(awaitables)

    async def leave_from_rooms(self, sender: ChatServerProcessor, *room_ids: int):
        self.remove_from_rooms(sender, *room_ids)
        for room_id in room_ids:
            message = SystemMessage.make(sender, SystemMessage.USER_LEAVE, user_id=sender.user_id, room_id=room_id, user_name=sender.user_name).serialize()
            awaitables = [chat_server_processor.send_message(message) for chat_server_processor in self.__room_clients[room_id] if chat_server_processor != sender]
            if awaitables:
                await asyncio.wait(awaitables)

    def add_to_rooms(self, chat_server_processor: ChatServerProcessor, *room_ids: int):
        for room_id in room_ids:
            if chat_server_processor.add_to_room(room_id):
                self.__room_clients.setdefault(room_id, []).append(chat_server_processor)

    def remove_from_rooms(self, chat_server_processor: ChatServerProcessor, *room_ids: int):
        for room_id in chat_server_processor.room_ids:
            room_clients = self.__room_clients.get(room_id)
            if not room_clients:
                continue
            room_clients.remove(chat_server_processor)

    async def send_message(self, message: models.Message, sender: ChatServerProcessor):
        users = self.all_chat_users(sender, message.room_id)
        if not users:
            return
        response = MessageInfo.make(sender, message.room_id, message.client_data()).serialize()
        awaitables = [chat_server_processor.send_message(response) for chat_server_processor in users]
        await asyncio.wait(awaitables)

    async def send_message_edited(self, message: models.Message, sender: ChatServerProcessor):
        users = self.all_chat_users(sender, message.room_id)
        if not users:
            return
        response = SystemMessage.make(sender, SystemMessage.MESSAGE_EDITED, message=message.client_data()).serialize()
        awaitables = [chat_server_processor.send_message(response) for chat_server_processor in users]
        await asyncio.wait(awaitables)

    async def added_to_room(self, sender: ChatServerProcessor, user_id: int, room: models.Room):
        user_processors = self.__clients.get(user_id)
        if not user_processors:
            return
        for user_processor in user_processors:
            self.add_to_rooms(user_processor, room.id)
        response = self._make_system_message(sender, SystemMessage.ADDED_TO_ROOM, room=room.client_data())
        await self._send_message(user_processors, response, sender)

    async def added_contact(self, current: ChatServerProcessor, receiver_id: int, contact_id: int, user: models.User, room: models.Room):
        user_processors = self.__clients.get(receiver_id)
        if not user_processors:
            return
        for user_processor in user_processors:
            self.add_to_rooms(user_processor, room.id)
        response = self._make_system_message(current, SystemMessage.ADDED_CONTACT, contact_id=contact_id, user=user.chat_client_data(), room=room.client_data())
        await self._send_message(user_processors, response, current)

    async def removed_contact(self, current: ChatServerProcessor, receiver_id: int, contact_id: int, room_id: int):
        user_processors = self.__clients.get(receiver_id)
        if not user_processors:
            return
        response = self._make_system_message(current, SystemMessage.REMOVED_CONTACT, contact_id=contact_id, room_id=room_id)
        await self._send_message(user_processors, response, current)

    def _make_system_message(self, current: ChatServerProcessor, message_id: int, **parameters):
        return SystemMessage.make(current, message_id, **parameters).serialize()

    async def _send_message(self, processors: List[ChatServerProcessor], response: str, current: ChatServerProcessor = None):
        awaitables = [chat_server_processor.send_message(response) for chat_server_processor in processors if chat_server_processor != current]
        if not awaitables:
            return
        await asyncio.wait(awaitables)



