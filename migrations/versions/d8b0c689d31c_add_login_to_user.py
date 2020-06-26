"""add login to user

Revision ID: d8b0c689d31c
Revises: 858aab632420
Create Date: 2020-06-17 16:15:20.278621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8b0c689d31c'
down_revision = '858aab632420'
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.add_column('users', sa.Column('login', sa.String(50), nullable=False))
    op.create_index('users_login_index', 'users', ['login'], unique=True)


def downgrade(engine_name=None):
    op.drop_column('users', 'login')
