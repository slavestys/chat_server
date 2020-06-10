from __future__ import annotations
from typing import List, Optional
from tortoise.models import Model
from tortoise import fields, queryset
from tortoise.query_utils import Q

class Contact(Model):
    id = fields.IntField(pk=True)
    user1_id = fields.IntField()
    user2_id = fields.IntField()
    contact_enabled = fields.BooleanField(default=True)

    class Meta:
        table = 'contacts'

    @classmethod
    def find_contact(cls, user1_id: int, user2_id: int) -> queryset.QuerySetSingle[Optional[Contact]]:
        return cls.filter(Q(Q(user1_id=user1_id, user2_id=user2_id), Q(user1_id=user2_id, user2_id=user1_id), join_type='OR')).get_or_none()

    @classmethod
    def find_contacts(cls, user_id: int, enabled_only: bool = False) -> queryset.QuerySet[Contact]:
        query_set = cls.filter(Q(user1_id=user_id, user2_id=user_id, join_type='OR'))
        if enabled_only:
            query_set = query_set.filter(contact_enabled=True)
        return query_set.all()

    def client_data(self, current_user_id: int):
        return {
            'id': self.id,
            'user_id': self.user1_id if current_user_id == self.user2_id else self.user2_id,
            'enabled': self.contact_enabled
        }