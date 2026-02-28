# mako template for Alembic migration scripts
"""
Revision ID: b64241945d63
Revises: add_game_id_to_injuries_20260228, 2d89c4779e84
Create Date: 2026-02-28 14:58:55.497116
"""
revision = "b64241945d63"
down_revision = ('add_game_id_to_injuries_20260228', '2d89c4779e84')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    pass

def downgrade():
    pass
