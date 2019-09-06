"""Add longtimeout table

Revision ID: 1260bfd2786f
Revises: a8ad6e7fadd6
Create Date: 2019-06-14 13:53:45.083821

"""

# revision identifiers, used by Alembic.
revision = "1260bfd2786f"
down_revision = "a8c7ec3b898d"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.create_table('tb_longtimeout',
    sa.Column('username', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32), nullable=False),
    sa.Column('timeout_start', mysql.DATETIME(), nullable=False),
    sa.Column('timeout_recent_end', mysql.DATETIME()),
    sa.Column('timeout_end', mysql.DATETIME(), nullable=False),
    sa.Column('timeout_author', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32), nullable=False),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('username_UNIQUE', 'tb_longtimeout', ['username'], unique=True)

def downgrade():
    op.drop_index('username_UNIQUE', table_name='tb_longtimeout')
    op.drop_table('tb_longtimeout')
