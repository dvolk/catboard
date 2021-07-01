"""initial migration

Revision ID: 2be801a4a7a8
Revises: 
Create Date: 2021-07-01 10:13:20.896602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2be801a4a7a8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('board',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lane',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('board_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['board_id'], ['board.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('column',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('lane_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['lane_id'], ['lane.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('assigned', sa.String(length=64), nullable=False),
    sa.Column('color', sa.String(length=64), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
    sa.Column('column_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['column_id'], ['column.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('item')
    op.drop_table('column')
    op.drop_table('lane')
    op.drop_table('board')
    # ### end Alembic commands ###
