import pytest
import aiohttp
import asyncio
import pytest
import tortoise

import chat
from .utils import TestChatServer, TestChatClient


@pytest.fixture(scope="session")
def loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
async def chat_server_fixture(loop):
    test_server = TestChatServer()
    await test_server.start_server()
    yield test_server


@pytest.fixture(scope='function')
async def chat_server(chat_server_fixture: TestChatServer):
    yield chat_server_fixture
    async with tortoise.transactions.in_transaction() as connection:
        await connection.execute_query('SELECT truncate_tables();')
    state = chat_server_fixture.state
    clients = state.clients.copy()
    for client_id, user_clients in clients.items():
        for client in user_clients:
            await client.close()
    state.clients.clear()
    state.room_clients.clear()
    state.unauthorized.clear()


@pytest.fixture(scope='function')
async def chat_client_fixture(chat_server: TestChatServer):
    async with TestChatClient(chat_server.test_server) as client:
        yield client


