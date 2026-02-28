"""
Add game_id column to injuries table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_game_id_to_injuries_20260228'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('injuries', sa.Column('game_id', sa.String(length=64), nullable=True))
    op.create_index('ix_injuries_game_id', 'injuries', ['game_id'])
    op.create_foreign_key(
        None, 'injuries', 'games', ['game_id'], ['game_id'], ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint(None, 'injuries', type_='foreignkey')
    op.drop_index('ix_injuries_game_id', table_name='injuries')
    op.drop_column('injuries', 'game_id')
