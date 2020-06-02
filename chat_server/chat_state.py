from typing import List, Dict, Set
import json
import asyncio

from .chat_server_processor import ChatServerProcessor
from chat_common.protocol import SystemMessage, Message, MessageEdit, MessageInfo
import models


class ChatState:
    __clients: List[ChatServerProcessor]
    __room_clients: Dict[int, List[ChatServerProcessor]]

    def __init__(self):
        self.__clients = []
        self.__room_clients = {}

    def all_chat_users(self, sender: ChatServerProcessor, *room_ids: int) -> Set[ChatServerProcessor]:
        chat_users = set()
        for room_id in room_ids:
            for chat_server_processor in self.__room_clients[room_id]:
                if chat_server_processor == sender:
                    continue
                chat_users.add(chat_server_processor)
        return chat_users

    def add_user(self, chat_server_processor: ChatServerProcessor):
        self.__clients.append(chat_server_processor)

    async def online(self, sender: ChatServerProcessor):
        self.add_to_rooms(sender, *sender.room_ids)
        message = SystemMessage.make(sender, SystemMessage.USER_ONLINE, user_id=sender.user_id, user_name=sender.user_name).serialize()
        awaitables = [chat_server_processor.send_message(message) for chat_server_processor in self.all_chat_users(sender, *sender.room_ids)]
        if not awaitables:
            return
        await asyncio.wait(awaitables)

    async def offline(self, sender: ChatServerProcessor):
        self.__clients.remove(sender)
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
        self.__clients.append(chat_server_processor)
        for room_id in room_ids:
            self.__room_clients.setdefault(room_id, []).append(chat_server_processor)

    def remove_from_rooms(self, chat_server_processor: ChatServerProcessor, *room_ids: int):
        self.__clients.remove(chat_server_processor)
        for room_id in chat_server_processor.room_ids:
            self.__room_clients[room_id].remove(chat_server_processor)

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


