"""create users rooms table

Revision ID: 9548d09411d4
Revises: 7af15ec9092b
Create Date: 2020-04-29 13:15:13.772610

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9548d09411d4'
down_revision = '7af15ec9092b'
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.create_table(
        'users_rooms',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('room_id', sa.Integer, sa.ForeignKey('rooms.id'))
    )
    op.create_index('users_rooms_index', 'users_rooms', ['user_id', 'room_id'], unique=True)


def downgrade(engine_name=None):
    op.drop_table('users_rooms')
