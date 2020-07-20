from tortoise.models import Model
from tortoise import fields
import hashlib
import base64
import json

import config
from chat_common import protocol

class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)
    passwd = fields.CharField(50)
    rooms = fields.ManyToManyField('models.Room', forward_key='room_id', backward_key='user_id', related_name='users')
    login = fields.CharField(50)

    class Meta:
        table = 'users'

    def key(self) -> str:
        key = hashlib.sha256()
        key.update(config.secret_key)
        key.update(self.passwd.encode('utf-8'))
        return base64.b16encode(key.digest()).decode('utf-8')

    def client_data(self) -> protocol.User:
        user_protocol = protocol.User(id=self.id, name=self.name, login=self.login, key=self.key())
        return user_protocol

    def chat_client_data(self) -> protocol.User:
        user_protocol = protocol.User(id=self.id, name=self.name, login=self.login)
        return user_protocol

    def json_data(self) -> str:
        return json.dumps(self.client_data())

    def __repr__(self):
        return "<User(name='%s')>" % self.name


