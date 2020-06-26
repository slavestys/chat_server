from aiohttp.test_utils import TestServer

import chat
import chat_server


class TestChatServer:
    _test_server: TestServer
    _server: chat.ChatServer

    def __init__(self):
        self._server = chat.ChatServer()

    async def start_server(self):
        app = await self._server.setup_app()
        self._test_server = TestServer(app)
        await self._test_server.start_server()

    @property
    def test_server(self) -> TestServer:
        return self._test_server

    @property
    def server(self) -> chat.ChatServer:
        return self._server

    @property
    def chat(self) -> chat.Chat:
        return self._server.chat

    @property
    def state(self) -> chat_server.ChatState:
        return self._server.chat.state

    def url(self) -> str:
        return f'ws://{self._test_server.host}:{self._test_server.port}'