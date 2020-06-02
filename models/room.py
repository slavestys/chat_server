from tortoise.models import Model
from tortoise import fields


class Room(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)

    class Meta:
        table = 'rooms'

    def __repr__(self):
        return f'<Room(name=\'{self.name}\')>'


