import pytest
from collections import namedtuple

from chat_common import protocol
import models
from test.utils import TestChatServer, TestChatClient


PreparedData = namedtuple('PreparedData', 'user friend contact room')

@pytest.fixture(scope='function')
async def prepare_data():
    user = await models.User.create(name='test1', login='test1', passwd='1')
    friend = await models.User.create(name='test2', login='test2', passwd='1')
    contact = await models.Contact.create(user1_id=user.id, user2_id=friend.id)
    room = await models.Room.create(name=str(contact.id), room_type=protocol.Room.TYPE_USER)
    return PreparedData(user, friend, contact, room)


async def test_contact_remove_success(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
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

    command = protocol.ContactRemove.make(None, prepare_data.friend.id)
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    room = await models.Room.get()
    contact = await models.Contact.get()
    assert room.room_enabled is False
    assert contact.contact_enabled is False
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'system_message',
        'contact_id': contact.id,
        'message': 'ok',
        'message_id': protocol.SystemMessage.COMMAND_SUCCESS,
        'room_id': room.id
    }

    response = await friend_client.recv_message()
    assert response == {
        'command': 'system_message',
        'contact_id': contact.id,
        'message': 'removed_contact',
        'message_id': protocol.SystemMessage.REMOVED_CONTACT,
        'room_id': room.id
    }

    command = protocol.ContactRemove.make(None, prepare_data.friend.id)
    command.cmd_id = 3
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'Contact not exists',
        'error_code': protocol.Error.ERR_CONTACT_NOT_EXISTS
    }


async def test_contact_remove_error_not_authenticated(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    command = protocol.ContactRemove.make(None, prepare_data.friend.id)
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    room = await models.Room.get_or_none()
    contact = await models.Contact.get_or_none()
    assert room.room_enabled
    assert contact.contact_enabled
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'Authentication need',
        'error_code': protocol.Error.ERR_AUTH_NEED
    }

async def test_contact_remove_error_user_not_found(chat_server: TestChatServer, chat_client_fixture: TestChatClient, prepare_data: PreparedData):
    command = protocol.Auth.make(None, prepare_data.user.login, prepare_data.user.passwd)
    command.cmd_id = 1
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response['message'] == 'auth success'

    command = protocol.ContactRemove.make(None, -1)
    command.cmd_id = 2
    await chat_client_fixture.send_message(command.data)
    response = await chat_client_fixture.recv_message()
    assert response == {
        'cmd_id': command.cmd_id,
        'command': 'error',
        'error': 'User not found',
        'error_code': protocol.Error.ERR_USER_NOT_FOUND
    }