import aiohttp
from aiohttp.test_utils import TestClient, BaseTestServer
from aiohttp import web
import asyncio
import json


class TestChatClient:
    _server: BaseTestServer
    _websocket: aiohttp.ClientWebSocketResponse = None
    _message_event: asyncio.Future
    _connected_event: asyncio.Future
    _loop: asyncio.AbstractEventLoop = None
    _messages_queue: list
    _task: asyncio.Task = None

    def __init__(self, server: BaseTestServer):
        self._server = server
        self._message_event = asyncio.Future()
        self._connected_event = asyncio.Future()
        self._messages_queue = []
        super(TestChatClient, self).__init__()

    async def connect(self):
        self._loop = asyncio.get_running_loop()
        client = TestClient(self._server)
        async with client.ws_connect('/') as websocket:
            try:
                self._websocket = websocket
                self._connected_event.set_result(True)
                async for request in websocket:
                    self._messages_queue.append(request)
                    self._message_event.set_result(True)
            except asyncio.CancelledError:
                await self.stop()

    async def recv_message_raw(self):
        if not self._message_event.done():
            await self._message_event
        res = self._messages_queue.pop()
        if not self._messages_queue:
            self._message_event = asyncio.Future()
        return res

    async def recv_message(self):
        raw_message = await self.recv_message_raw()
        return json.loads(raw_message.data)

    def send_message(self, message: dict):
        return self._websocket.send_str(json.dumps(message))

    async def wait_connection(self):
        await self._connected_event

    def stop(self):
        return self._websocket.close()

    async def start(self):
        self._task = asyncio.create_task(self.connect())
        await self.wait_connection()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._task.cancel()