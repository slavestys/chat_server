from tortoise.models import Model
from tortoise import fields
import hashlib
import base64
import json

import config

class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)
    passwd = fields.CharField(50)
    rooms = fields.ManyToManyField('models.Room', forward_key='room_id', backward_key='user_id', related_name='users')

    class Meta:
        table = 'users'

    def key(self) -> str:
        key = hashlib.sha256()
        key.update(config.secret_key)
        key.update(self.passwd.encode('utf-8'))
        return base64.b16encode(key.digest()).decode('utf-8')

    def client_data(self) -> dict:
        return {'id': self.id, 'name': self.name, 'key': self.key()}

    def chat_client_data(self) -> dict:
        return {'id': self.id, 'name': self.name}

    def json_data(self) -> str:
        return json.dumps(self.client_data())

    def __repr__(self):
        return "<User(name='%s')>" % self.name


