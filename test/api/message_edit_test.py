import pytest
import datetime
from collections import namedtuple

from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


PreparedData = namedtuple('PreparedData', 'room user friend message')

@pytest.fixture(scope='function')
async def prepare_data():
    room = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    user = await models.User.create(name='test1', login='test1', passwd='1')
    await user.rooms.add(room)
    friend = await models.User.create(name='test2', login='test2', passwd='1')
    await friend.rooms.add(room)
    message = await models.Message.create(room_id=room.id, message='test message', user_id=user.id, created_at=datetime.datetime.now())
    return PreparedData(room, user, friend, message)


async def test_message_edit_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    friend_client = TestChatClient(chat_server.test_server)
    await friend_client.start()

    command = protocol.Auth.make(None, prepare_data.user.login, prepare_data.user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.Auth.make(None, prepare_data.friend.login, prepare_data.friend.passwd)
    command.cmd_id = 1
    await friend_client.send_message(command.data)
    response = await friend_client.recv_message()
    assert response['message'] == 'auth success'

    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'user online'

    command = protocol.MessageEdit.make(None, prepare_data.message.id, 'new message_text')
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'system_message',
        'message': 'ok',
        'message_id': protocol.SystemMessage.COMMAND_SUCCESS
    }

    message = prepare_data.message
    message_edited = await models.Message.get(id=message.id)
    assert message_edited.message == 'new message_text'
    response = await friend_client.recv_message()
    assert response == {
        'command': 'system_message',
        'message': {
            'created_at': int(message.created_at.timestamp()),
            'created_at_str': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'id': message.id,
            'message': 'new message_text',
            'user_id': message.user_id
        },
        'message_id': 7
    }

async def test_message_edit_error_not_authenticated(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    command = protocol.MessageEdit.make(None, prepare_data.message.id, 'new message_text')
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'Authentication need',
        'error_code': protocol.Error.ERR_AUTH_NEED
    }

    message_edited = await models.Message.get(id=prepare_data.message.id)
    assert message_edited.message == prepare_data.message.message


async def test_message_edit_error_not_found(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    command = protocol.Auth.make(None, prepare_data.user.login, prepare_data.user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.MessageEdit.make(None, -1, 'new message_text')
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'Message not found',
        'error_code': protocol.Error.ERR_MESSAGE_NOT_FOUND
    }

    message_edited = await models.Message.get(id=prepare_data.message.id)
    assert message_edited.message == prepare_data.message.message


async def test_message_edit_error_cant_edit(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    friend_client = TestChatClient(chat_server.test_server)
    await friend_client.start()

    command = protocol.Auth.make(None, prepare_data.friend.login, prepare_data.friend.passwd)
    command.cmd_id = 1
    await friend_client.send_message(command.data)
    response = await friend_client.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.MessageEdit.make(None, prepare_data.message.id, 'new message_text')
    command.cmd_id = 2
    await friend_client.send_message(command.data)
    response = await friend_client.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': "Can't edit message",
        'error_code': protocol.Error.ERR_CAN_T_EDIT_MESSAGE
    }

    message_edited = await models.Message.get(id=prepare_data.message.id)
    assert message_edited.message == prepare_data.message.message

