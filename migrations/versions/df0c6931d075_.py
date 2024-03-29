"""empty message

Revision ID: df0c6931d075
Revises: cfaf9c6189e0
Create Date: 2023-08-22 09:12:04.314732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "df0c6931d075"
down_revision = "cfaf9c6189e0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "cal_day",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date_str", sa.String(length=10), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], "fa_user_id_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("cal_day", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_cal_day_date_str"), ["date_str"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_cal_day_user_id"), ["user_id"], unique=False
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cal_day", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cal_day_user_id"))
        batch_op.drop_index(batch_op.f("ix_cal_day_date_str"))

    op.drop_table("cal_day")
    # ### end Alembic commands ###
