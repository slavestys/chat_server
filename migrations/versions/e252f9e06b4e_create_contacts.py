"""create_contacts

Revision ID: e252f9e06b4e
Revises: cf0373a66fe7
Create Date: 2020-06-10 12:59:48.325058

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e252f9e06b4e'
down_revision = 'cf0373a66fe7'
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user1_id', sa.Integer, nullable=False),
        sa.Column('user2_id', sa.Integer, nullable=False)
    )
    op.create_index('contacts_users_index', 'contacts', ['user1_id', 'user2_id'], unique=True)


def downgrade(engine_name=None):
    op.drop_table('rooms')
