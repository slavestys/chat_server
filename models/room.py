from tortoise.models import Model
from tortoise import fields


class Room(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)
    room_type = fields.IntField()
    room_enabled = fields.BooleanField(default=True)

    class Meta:
        table = 'rooms'

    def __repr__(self):
        return f'<Room(name=\'{self.name}\')>'

    def client_data(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.room_type,
            'enabled': self.room_enabled
        }