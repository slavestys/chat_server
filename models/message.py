from tortoise.models import Model
from tortoise import fields

from chat_common import protocol


class Message(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    created_at = fields.DatetimeField()
    message = fields.TextField()
    room = fields.ForeignKeyField('models.Room', related_name='messages')

    class Meta:
        table = 'messages'

    def client_data(self):
        protocol_message = protocol.Message(self.id, self.user_id, self.message, self.created_at)
        return protocol_message.to_dict()

    def __repr__(self):
        return f'<Message(name=\'{self.message}\')>'


