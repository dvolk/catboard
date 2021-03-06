"""empty message

Revision ID: 7b5bb1314f3b
Revises: 4648243e0bf6
Create Date: 2021-07-04 09:43:43.994525

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b5bb1314f3b'
down_revision = '4648243e0bf6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('board', sa.Column('closed', sa.Boolean(), nullable=False, server_default="0"))
    op.add_column('column', sa.Column('closed', sa.Boolean(), nullable=False, server_default="0"))
    op.add_column('lane', sa.Column('closed', sa.Boolean(), nullable=False, server_default="0"))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lane', 'closed')
    op.drop_column('column', 'closed')
    op.drop_column('board', 'closed')
    # ### end Alembic commands ###
