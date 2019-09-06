"""remove_highlights

Revision ID: 186928676dbc
Revises: f163a00a02aa
Create Date: 2019-06-01 15:14:13.999836

"""

# revision identifiers, used by Alembic.
revision = "186928676dbc"
down_revision = "f163a00a02aa"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("tb_stream_chunk_highlight")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "tb_stream_chunk_highlight",
        sa.Column("id", mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column("stream_chunk_id", mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.Column("created_at", mysql.DATETIME(), nullable=False),
        sa.Column("highlight_offset", mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.Column("description", mysql.VARCHAR(length=128), nullable=True),
        sa.Column("override_link", mysql.VARCHAR(length=256), nullable=True),
        sa.Column("thumbnail", mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
        sa.Column("created_by", mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
        sa.Column("last_edited_by", mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(["stream_chunk_id"], ["tb_stream_chunk.id"], name="tb_stream_chunk_highlight_ibfk_1"),
        sa.PrimaryKeyConstraint("id"),
        mysql_default_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    # ### end Alembic commands ###