from tortoise.models import Model
from tortoise import fields

from chat_common import protocol


class Room(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)
    room_type = fields.IntField()
    room_enabled = fields.BooleanField(default=True)

    class Meta:
        table = 'rooms'

    def __repr__(self):
        return f'<Room(name=\'{self.name}\')>'

    def client_data(self, messages_client_data: list = None):
        room_protocol = protocol.Room(
            id=self.id,
            name=self.name,
            type=self.room_type,
            enabled=bool(self.room_enabled),
            messages=messages_client_data
        )
        return room_protocol.to_dict()