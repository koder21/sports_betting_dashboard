"""Add new fields to bets table for parlay tracking and betting analysis

This migration adds:
- parlay_id: To group bets into parlays
- stat_type: For prop bets to track stat type (points, rebounds, assists, etc)
- player_name: To store player name for bets
- reason: To store the reasoning behind each bet

Revision ID: 0003_add_bet_fields
Revises: 0002_convert_text_datetimes
Create Date: 2026-02-07 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_bet_fields'
down_revision = '0002_convert_text_datetimes'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.add_column(sa.Column('parlay_id', sa.String(128), nullable=True))
        batch_op.add_column(sa.Column('stat_type', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('player_name', sa.String(128), nullable=True))
        batch_op.add_column(sa.Column('reason', sa.String(512), nullable=True))


def downgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.drop_column('reason')
        batch_op.drop_column('player_name')
        batch_op.drop_column('stat_type')
        batch_op.drop_column('parlay_id')
