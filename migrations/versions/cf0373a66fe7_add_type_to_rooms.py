"""add type to rooms

Revision ID: cf0373a66fe7
Revises: 9548d09411d4
Create Date: 2020-06-10 12:42:57.604293

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf0373a66fe7'
down_revision = '9548d09411d4'
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.add_column('rooms', sa.Column('room_type', sa.Integer, server_default='1', nullable=False))


def downgrade(engine_name=None):
    op.drop_column('rooms', 'room_type')
