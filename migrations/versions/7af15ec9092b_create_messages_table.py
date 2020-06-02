"""create messages table

Revision ID: 7af15ec9092b
Revises: 2ae390ef4168
Create Date: 2020-04-28 16:24:49.419456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7af15ec9092b'
down_revision = '2ae390ef4168'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer),
        sa.Column('room_id', sa.Integer),
        sa.Column('message', sa.Text),
        sa.Column('created_at', sa.DateTime)
    )
    op.create_index('messages_user_id_room_id_created_at_index', 'messages', ['user_id', 'room_id', 'created_at'])


def downgrade():
    op.drop_table('messages')
