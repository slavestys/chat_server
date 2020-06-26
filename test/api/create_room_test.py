import pytest
from collections import namedtuple

from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


PreparedData = namedtuple('PreparedData', 'user')


@pytest.fixture(scope='function')
async def prepare_data():
    user = await models.User.create(name='test1', login='test1', passwd='1')
    return PreparedData(user)


async def test_create_room_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    command = protocol.Auth.make(None, prepare_data.user.login, prepare_data.user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    room_name = 'test room'
    command = protocol.RoomCreate.make(None, room_name)
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    room = await models.Room.get()
    assert room.name == room_name
    assert response == {
        'cmd_id': 2,
        'command': 'system_message',
        'message': 'ok',
        'message_id': protocol.SystemMessage.COMMAND_SUCCESS,
        'room_id': room.id
    }

async def test_create_room_error_not_authenticated(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    room_name = 'test room'
    command = protocol.RoomCreate.make(None, room_name)
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    room = await models.Room.get_or_none()
    assert room is None
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'Authentication need',
        'error_code': protocol.Error.ERR_AUTH_NEED
    }