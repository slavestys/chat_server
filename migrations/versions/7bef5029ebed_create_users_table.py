"""create users table

Revision ID: 7bef5029ebed
Revises: 
Create Date: 2020-04-28 15:28:03.253337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7bef5029ebed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade(engine_name=None):
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('passwd', sa.String(50), nullable=False)
    )

def downgrade(engine_name=None):
    op.drop_table('users')
