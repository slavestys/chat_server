from tortoise.models import Model
from tortoise import fields


class UserRoom(Model):
    user_id = fields.IntField(pk=True)
    room_id = fields.IntField()

    class Meta:
        table = 'users_rooms'

    def __repr__(self):
        return f'<UserRoom(user_id=\'{self.user_id}\', room_id=\'{self.room_id}\')>'


