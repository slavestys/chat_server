from aiohttp import web
from tortoise import Tortoise

from .chat_server_processor import ChatServerProcessor
from .chat_state import ChatState


class Chat:
    __state: ChatState

    def __init__(self):
        self.__state = ChatState()

    async def accept(self, request):
        print('Client connected')
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        chat_server_processor = ChatServerProcessor(ws, self.__state)
        self.__state.add_user(chat_server_processor)
        await chat_server_processor.loop()
        print('Client disconnected')

    async def shutdown(self, _app):
        await Tortoise.close_connections()
