"""Add original_stake field to track parlay stake

Revision ID: 0005_add_original_stake
Revises: 0004_add_parlay_odds
Create Date: 2026-02-07 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_original_stake'
down_revision = '0004_add_parlay_odds'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.add_column(sa.Column('original_stake', sa.Float(), nullable=True))
    
    # Backfill original_stake with current stake value
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE bets SET original_stake = stake WHERE original_stake IS NULL"))


def downgrade():
    with op.batch_alter_table('bets') as batch_op:
        batch_op.drop_column('original_stake')
