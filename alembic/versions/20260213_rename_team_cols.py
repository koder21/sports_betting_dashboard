"""
Rename home_team and away_team columns to home_team_name and away_team_name in games_upcoming table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260213_rename_team_cols'
down_revision = None  # Set this to the previous migration's revision id if you have one
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns WHERE table_name='games_upcoming'
    """))
    columns = [row[0] for row in result]
    if 'home_team' in columns:
        op.execute('ALTER TABLE games_upcoming RENAME COLUMN home_team TO home_team_name')
    if 'away_team' in columns:
        op.execute('ALTER TABLE games_upcoming RENAME COLUMN away_team TO away_team_name')

def downgrade():
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns WHERE table_name='games_upcoming'
    """))
    columns = [row[0] for row in result]
    if 'home_team_name' in columns:
        op.execute('ALTER TABLE games_upcoming RENAME COLUMN home_team_name TO home_team')
    if 'away_team_name' in columns:
        op.execute('ALTER TABLE games_upcoming RENAME COLUMN away_team_name TO away_team')
