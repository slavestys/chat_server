from tortoise.models import Model
from tortoise import fields


class Message(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    created_at = fields.DatetimeField()
    message = fields.TextField()
    room = fields.ForeignKeyField('models.Room', related_name='messages')

    class Meta:
        table = 'messages'

    def client_data(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'created_at': int(self.created_at.timestamp()),
            'created_at_str': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<Message(name=\'{self.message}\')>'


