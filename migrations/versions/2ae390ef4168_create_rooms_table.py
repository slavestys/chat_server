"""create rooms table

Revision ID: 2ae390ef4168
Revises: 7bef5029ebed
Create Date: 2020-04-28 16:24:43.583044

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ae390ef4168'
down_revision = '7bef5029ebed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False)
    )


def downgrade():
    op.drop_table('rooms')
