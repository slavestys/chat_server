"""add_enabled_to_contacts

Revision ID: 858aab632420
Revises: 6a998c323a86
Create Date: 2020-06-16 15:49:15.848340

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '858aab632420'
down_revision = '6a998c323a86'
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.add_column('contacts', sa.Column('contact_enabled', sa.BOOLEAN, server_default='True', nullable=False))


def downgrade(engine_name=None):
    op.drop_column('contacts', 'contact_enabled')
