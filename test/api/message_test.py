import pytest
import asyncio

from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


async def test_message_send_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, friend_client: TestChatClient):
    room = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    user = await models.User.create(name='test1', login='test1', passwd='1')
    await user.rooms.add(room)
    friend = await models.User.create(name='test2', login='test2', passwd='1')
    await friend.rooms.add(room)

    command = protocol.Auth.make(None, user.login, user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.Auth.make(None, friend.login, friend.passwd)
    command.cmd_id = 1
    await friend_client.send_message(command.data)
    response = await friend_client.recv_message()
    assert response['message'] == 'auth success'

    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'user online'

    command = protocol.MessageCreate.make(None, room.id, 'Test message')
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    message = await models.Message.get()
    assert message.message == command.message
    assert message.user_id == user.id
    assert message.room_id == room.id
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'system_message',
        'data': {
            'created_at': int(message.created_at.timestamp()),
            'created_at_str': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'id': message.id,
            'message': message.message,
            'user_id': message.user_id
        },
        'message': 'ok',
        'message_id': 5
    }

    response = await friend_client.recv_message()
    assert response == {
        'command': 'message_info',
        'message': {
            'created_at': int(message.created_at.timestamp()),
            'created_at_str': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'id': message.id,
            'message': message.message,
            'user_id': message.user_id
        },
        'room_id': room.id
    }


async def test_message_send_error_not_authenticated(chat_server: TestChatServer, chat_client_fixture: TestChatClient):
    room = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    user = await models.User.create(name='test1', login='test1', passwd='1')

    command = protocol.MessageCreate.make(None, room.id, 'Test message')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    message = await models.Message.get_or_none()
    assert message is None
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Authentication need', 'error_code': protocol.Error.ERR_AUTH_NEED}


async def test_message_send_error_not_in_room(chat_server: TestChatServer, chat_client_fixture: TestChatClient):
    room = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    user = await models.User.create(name='test1', login='test1', passwd='1')

    command = protocol.Auth.make(None, user.login, user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.MessageCreate.make(None, room.id, 'Test message')
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    message = await models.Message.get_or_none()
    assert message is None
    assert response == {'cmd_id': 2, 'command': 'error', 'error': 'User not in room', 'error_code': protocol.Error.ERR_USER_NOT_IN_ROOM}


async def test_message_send_error_message_blank(chat_server: TestChatServer, chat_client_fixture: TestChatClient):
    room = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    user = await models.User.create(name='test1', login='test1', passwd='1')
    await user.rooms.add(room)

    command = protocol.Auth.make(None, user.login, user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.MessageCreate.make(None, room.id, '')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    message = await models.Message.get_or_none()
    assert message is None
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Message empty', 'error_code': protocol.Error.ERR_MESSAGE_EMPTY}