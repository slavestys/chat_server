import pytest
import datetime
from collections import namedtuple
from typing import Optional

import chat
from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


PreparedData = namedtuple('PreparedData', 'user contact_user1 contact_user2 contact1 contact2 contact1_room contact2_room')


@pytest.fixture(scope='function')
async def create_user(chat_server: TestChatClient):
    user = await models.User.create(name='test1', login='test1', passwd='1')
    contact_user1 = await models.User.create(name='test2', login='test2', passwd='1')
    contact_user2 = await models.User.create(name='test3', login='test3', passwd='1')
    contact1 = await models.Contact.create(user1_id=user.id, user2_id=contact_user1.id)
    room_name = str(contact1.id)
    private_room = await models.Room.create(name=room_name, room_type=protocol.Room.TYPE_USER)
    await models.UserRoom.create(user_id=user.id, room_id=private_room.id)
    await models.UserRoom.create(user_id=contact_user1.id, room_id=private_room.id)
    contact2 = await models.Contact.create(user1_id=contact_user2.id, user2_id=user.id)
    room_name2 = str(contact2.id)
    private_room2 = await models.Room.create(name=room_name2, room_type=protocol.Room.TYPE_USER)
    await models.UserRoom.create(user_id=contact_user2.id, room_id=private_room2.id)
    await models.UserRoom.create(user_id=user.id, room_id=private_room2.id)
    room1 = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    await user.rooms.add(room1)
    message = await models.Message.create(room_id=room1.id, message='test message', user_id=user.id, created_at=datetime.datetime.now())
    room2 = await models.Room.create(name="test_room2", room_type=protocol.Room.TYPE_CHAT)
    prepared_data = PreparedData(user, contact_user1, contact_user2, contact1, contact2, private_room, private_room2)
    return prepared_data


async def check_auth_response(command, response, create_user: PreparedData, online:Optional[dict] = None):
    if not online:
        online = {}
    user = create_user.user
    rooms = await user.rooms
    assert len(rooms) == 3
    contact1 = create_user.contact1
    contact_user1 = create_user.contact_user1
    contact2 = create_user.contact2
    contact_user2 = create_user.contact_user2
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'system_message',
        'contacts': [
            {'enabled': True, 'id': contact1.id, 'user_id': contact1.user2_id},
            {'enabled': True, 'id': contact2.id, 'user_id': contact2.user1_id}
        ],
        'message': 'auth success',
        'message_id': protocol.SystemMessage.AUTH_SUCCESS,
        'rooms': [{'enabled': True, 'id': room.id, 'name': room.name, 'type': room.room_type, 'messages': [{
            'id': message.id,
            'user_id': message.user_id,
            'message': message.message,
            'created_at': int(message.created_at.timestamp()),
            'created_at_str': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for message in await room.messages]} for room in rooms],
        'user': {'id': user.id, 'login': user.login, 'name': user.name},
        'users': [
            {'id': user.id, 'login': user.login, 'name': user.name, 'online': bool(online.get(user.id))},
            {'id': contact_user1.id, 'login': contact_user1.login, 'name': contact_user1.name, 'online': bool(online.get(contact_user1.id))},
            {'id': contact_user2.id, 'login': contact_user2.login, 'name': contact_user2.name, 'online': bool(online.get(contact_user2.id))}
        ]
    }


async def test_server_init(chat_server: TestChatServer):
    state = chat_server.state
    assert state.clients == {}
    assert state.room_clients == {}
    assert state.unauthorized == []


async def test_client_connect(chat_server: TestChatServer, chat_client_fixture: TestChatClient):
    state = chat_server.state
    assert state.clients == {}
    assert state.room_clients == {}
    assert len(state.unauthorized) == 1
    assert state.unauthorized[0].is_authenticated() is False


async def test_client_auth_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, friend_client: TestChatClient, create_user: PreparedData):
    friend = create_user.contact_user1
    command = protocol.Auth.make(None, friend.login, friend.passwd)
    command.cmd_id = 1
    await friend_client.send_message(command.data)
    response = await friend_client.recv_message()
    assert response['message'] == 'auth success'

    user =create_user.user
    command = protocol.Auth.make(None, user.login, user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    await check_auth_response(command, response, create_user, online={create_user.contact_user1.id: True})
    state = chat_server.state
    assert list(state.clients.keys()).sort() == [user.id, friend.id].sort()
    assert len(state.clients[user.id]) == 1
    processor = state.clients[user.id][0]
    assert processor.user_id == user.id
    rooms = await user.rooms
    room_ids = [room.id for room in rooms]
    assert list(state.room_clients.keys()) == room_ids
    for room_id in room_ids:
        if room_id == create_user.contact1_room.id:
            assert len(state.room_clients[room_id]) == 2
        else:
            assert len(state.room_clients[room_id]) == 1
            assert state.room_clients[room_id][0].user_id == user.id
    assert state.unauthorized == []
    assert processor.is_authenticated()

    async with TestChatClient(chat_server.test_server) as friend_client2:
        contact_user = create_user.contact_user2
        command = protocol.Auth.make(None, contact_user.login, contact_user.passwd)
        command.cmd_id = 1
        await friend_client2.send_message(command.data)
        response = await friend_client2.recv_message()
        assert response['message'] == 'auth success'

        response = await chat_client_fixture.recv_message()
        assert response == {
            'command': 'system_message',
            'message': 'user online',
            'message_id': protocol.SystemMessage.USER_ONLINE,
            'user_id': contact_user.id,
            'user_name': contact_user.name
        }


    response = await chat_client_fixture.recv_message()
    assert response == {
        'command': 'system_message',
        'message': 'user offline',
        'message_id': protocol.SystemMessage.USER_OFFLINE,
        'user_id': contact_user.id,
        'user_name': contact_user.name
    }


async def test_client_auth_error(chat_server: TestChatServer, chat_client_fixture: TestChatClient, create_user: PreparedData):
    command = protocol.Auth.make(None, create_user.user.login, 'wrong password')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Authentication failed', 'error_code': protocol.Error.ERR_AUTH_FAILED}


async def test_client_auth_by_key_success(chat_server: chat.ChatServer, chat_client_fixture: TestChatClient, create_user: PreparedData):
    user = create_user.user
    command = protocol.AuthByKey.make(None, user.id, user.key())
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    await check_auth_response(command, response, create_user)
    state = chat_server.state
    assert list(state.clients.keys()) == [user.id]
    assert len(state.clients[user.id]) == 1
    processor = state.clients[user.id][0]
    assert processor.user_id == user.id
    rooms = await user.rooms
    room_ids = [room.id for room in rooms]
    assert list(state.room_clients.keys()) == room_ids
    for room_id in room_ids:
        assert len(state.room_clients[room_id]) == 1
        assert state.room_clients[room_id][0].user_id == user.id
    assert state.unauthorized == []
    assert processor.is_authenticated()


async def test_client_auth_by_key_error(chat_server: chat.ChatServer, chat_client_fixture: TestChatClient, create_user: PreparedData):
    command = protocol.AuthByKey.make(None, create_user.user.id, 'wrong key')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Authentication failed', 'error_code': protocol.Error.ERR_AUTH_FAILED}