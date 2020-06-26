import pytest
import datetime

import chat
from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


@pytest.fixture(scope='function')
async def create_user(chat_server: TestChatClient):
    user = await models.User.create(name='test1', login='test1', passwd='1')
    contact_user = await models.User.create(name='test2', login='test2', passwd='1')
    contact_user2 = await models.User.create(name='test3', login='test3', passwd='1')
    contact = await models.Contact.create(user1_id=user.id, user2_id=contact_user.id)
    room_name = str(contact.id)
    private_room = await models.Room.create(name=room_name, room_type=protocol.Room.TYPE_USER)
    await models.UserRoom.create(user_id=user.id, room_id=private_room.id)
    await models.UserRoom.create(user_id=contact_user.id, room_id=private_room.id)
    await models.Contact.create(user1_id=contact_user2.id, user2_id=user.id)
    room1 = await models.Room.create(name="test_room1", room_type=protocol.Room.TYPE_CHAT)
    await user.rooms.add(room1)
    message = await models.Message.create(room_id=room1.id, message='test message', user_id=user.id, created_at=datetime.datetime.now())
    room2 = await models.Room.create(name="test_room2", room_type=protocol.Room.TYPE_CHAT)
    return user


async def check_auth_response(command, response, create_user):
    rooms = await create_user.rooms
    assert len(rooms) == 2
    contacts = await models.Contact.find_contacts(create_user.id)
    contact1 = contacts[0]
    contact_user1 = await models.User.get(id=contact1.user2_id)
    contact2 = contacts[1]
    contact_user2 = await models.User.get(id=contact2.user1_id)
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
        'user': {'id': create_user.id, 'login': create_user.login, 'name': create_user.name},
        'users': [
            {'id': create_user.id, 'login': create_user.login, 'name': create_user.name},
            {'id': contact_user1.id, 'login': contact_user1.login, 'name': contact_user1.name},
            {'id': contact_user2.id, 'login': contact_user2.login, 'name': contact_user2.name}
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


async def test_client_auth_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, create_user: models.User):
    command = protocol.Auth.make(None, create_user.login, create_user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    await check_auth_response(command, response, create_user)
    state = chat_server.state
    assert list(state.clients.keys()) == [create_user.id]
    assert len(state.clients[create_user.id]) == 1
    processor = state.clients[create_user.id][0]
    assert processor.user_id == create_user.id
    rooms = await create_user.rooms
    room_ids = [room.id for room in rooms]
    assert list(state.room_clients.keys()) == room_ids
    for room_id in room_ids:
        assert len(state.room_clients[room_id]) == 1
        assert state.room_clients[room_id][0].user_id == create_user.id
    assert state.unauthorized == []
    assert processor.is_authenticated()

    async with TestChatClient(chat_server.test_server) as friend_client:
        contacts = await models.Contact.find_contacts(create_user.id)
        contact = contacts[0]
        contact_user = await models.User.get(id=contact.user2_id)
        command = protocol.Auth.make(None, contact_user.login, contact_user.passwd)
        command.cmd_id = 1
        await friend_client.send_message(command.data)
        response = await friend_client.recv_message()
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


async def test_client_auth_error(chat_server: TestChatServer, chat_client_fixture: TestChatClient, create_user: models.User):
    command = protocol.Auth.make(None, create_user.login, 'wrong password')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Authentication failed', 'error_code': protocol.Error.ERR_AUTH_FAILED}


async def test_client_auth_by_key_success(chat_server: chat.ChatServer, chat_client_fixture: TestChatClient, create_user: models.User):
    command = protocol.AuthByKey.make(None, create_user.id, create_user.key())
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    await check_auth_response(command, response, create_user)
    state = chat_server.state
    assert list(state.clients.keys()) == [create_user.id]
    assert len(state.clients[create_user.id]) == 1
    processor = state.clients[create_user.id][0]
    assert processor.user_id == create_user.id
    rooms = await create_user.rooms
    room_ids = [room.id for room in rooms]
    assert list(state.room_clients.keys()) == room_ids
    for room_id in room_ids:
        assert len(state.room_clients[room_id]) == 1
        assert state.room_clients[room_id][0].user_id == create_user.id
    assert state.unauthorized == []
    assert processor.is_authenticated()


async def test_client_auth_by_key_error(chat_server: chat.ChatServer, chat_client_fixture: TestChatClient, create_user: models.User):
    command = protocol.AuthByKey.make(None, create_user.id, 'wrong key')
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {'cmd_id': 1, 'command': 'error', 'error': 'Authentication failed', 'error_code': protocol.Error.ERR_AUTH_FAILED}