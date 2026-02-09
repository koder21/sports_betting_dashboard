"""Add parlay_odds field to bets table

Revision ID: 0004_add_parlay_odds
Revises: 0003_add_bet_fields
Create Date: 2026-02-07 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_parlay_odds'
down_revision = '0003_add_bet_fields'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.add_column(sa.Column('parlay_odds', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.drop_column('parlay_odds')
