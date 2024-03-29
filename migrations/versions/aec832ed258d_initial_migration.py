"""Initial migration.

Revision ID: aec832ed258d
Revises: 
Create Date: 2022-09-21 22:35:55.659686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aec832ed258d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('board',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
    sa.Column('lanes_sorted', sa.String(length=512), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lane',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
    sa.Column('board_id', sa.Integer(), nullable=False),
    sa.Column('columns_sorted', sa.String(length=512), nullable=True),
    sa.ForeignKeyConstraint(['board_id'], ['board.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('column',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
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
    sa.Column('public', sa.Boolean(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('column_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['column_id'], ['column.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('item_relationship',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item1_id', sa.Integer(), nullable=False),
    sa.Column('item2_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item1_id'], ['item.id'], ),
    sa.ForeignKeyConstraint(['item2_id'], ['item.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('item_transition',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('from_column_id', sa.Integer(), nullable=True),
    sa.Column('to_column_id', sa.Integer(), nullable=False),
    sa.Column('epochtime', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['from_column_id'], ['column.id'], ),
    sa.ForeignKeyConstraint(['item_id'], ['item.id'], ),
    sa.ForeignKeyConstraint(['to_column_id'], ['column.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('item_transition')
    op.drop_table('item_relationship')
    op.drop_table('item')
    op.drop_table('column')
    op.drop_table('lane')
    op.drop_table('board')
    # ### end Alembic commands ###
