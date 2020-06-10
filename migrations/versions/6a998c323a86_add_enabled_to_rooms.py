"""add_enabled_to_rooms

Revision ID: 6a998c323a86
Revises: e252f9e06b4e
Create Date: 2020-06-16 13:41:27.779579

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a998c323a86'
down_revision = 'e252f9e06b4e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rooms', sa.Column('room_enabled', sa.BOOLEAN, server_default='True', nullable=False))


def downgrade():
    op.drop_column('rooms', 'room_enabled')
