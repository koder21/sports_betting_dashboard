"""Rename sport table to sports

Revision ID: 0001_rename_sport_table
Revises: 
Create Date: 2026-02-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_rename_sport_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check whether the 'sport' table exists; if not, skip the rename.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'sport' in tables and 'sports' not in tables:
        # Try a generic table rename; works on most DBs including SQLite
        try:
            op.rename_table('sport', 'sports')
        except Exception:
            # Fallback for DBs without rename support: execute raw SQL
            op.execute("ALTER TABLE sport RENAME TO sports")
    else:
        # Nothing to do (either already renamed or original table missing)
        pass


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'sports' in tables and 'sport' not in tables:
        try:
            op.rename_table('sports', 'sport')
        except Exception:
            op.execute("ALTER TABLE sports RENAME TO sport")
    else:
        pass
