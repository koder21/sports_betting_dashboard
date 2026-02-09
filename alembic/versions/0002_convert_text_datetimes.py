"""Convert text datetime columns to DateTime-compatible columns (draft)

This migration is a draft and provides a safe, non-destructive approach for
SQLite and other DBs where altering column types is limited.

Strategy (draft):
- Add new columns with _new suffix of type DATETIME.
- Copy values from existing TEXT columns to the new columns (no parsing change).
- After verification, optionally rename and drop old columns in a follow-up step.

Revision ID: 0002_convert_text_datetimes
Revises: 0001_rename_sport_table
Create Date: 2026-02-06 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from dateutil import parser as date_parser

# revision identifiers, used by Alembic.
revision = '0002_convert_text_datetimes'
down_revision = '0001_rename_sport_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add new datetime columns (nullable) and copy values as-is.
    # games_upcoming.scraped_at -> scraped_at_new
    with op.batch_alter_table('games_upcoming') as batch_op:
        batch_op.add_column(sa.Column('scraped_at_new', sa.DateTime(), nullable=True))
    # Backfill scraped_at_new by parsing existing text values
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT game_id, scraped_at FROM games_upcoming")).fetchall()
    for gid, scraped in rows:
        if scraped is None:
            continue
        try:
            dt = datetime.fromisoformat(scraped.replace('Z', '+00:00'))
        except Exception:
            try:
                dt = date_parser.parse(scraped)
            except Exception:
                dt = None
        if dt:
            conn.execute(
                sa.text("UPDATE games_upcoming SET scraped_at_new = :val WHERE game_id = :gid"),
                {"val": dt, "gid": gid},
            )

    # games_live.updated_at -> updated_at_new
    with op.batch_alter_table('games_live') as batch_op:
        batch_op.add_column(sa.Column('updated_at_new', sa.DateTime(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT game_id, updated_at FROM games_live")).fetchall()
    for gid, updated in rows:
        if updated is None:
            continue
        try:
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
        except Exception:
            try:
                dt = date_parser.parse(updated)
            except Exception:
                dt = None
        if dt:
            conn.execute(
                sa.text("UPDATE games_live SET updated_at_new = :val WHERE game_id = :gid"),
                {"val": dt, "gid": gid},
            )

    # games_results.moved_at -> moved_at_new
    with op.batch_alter_table('games_results') as batch_op:
        batch_op.add_column(sa.Column('moved_at_new', sa.DateTime(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT game_id, moved_at FROM games_results")).fetchall()
    for gid, moved in rows:
        if moved is None:
            continue
        try:
            dt = datetime.fromisoformat(moved.replace('Z', '+00:00'))
        except Exception:
            try:
                dt = date_parser.parse(moved)
            except Exception:
                dt = None
        if dt:
            conn.execute(
                sa.text("UPDATE games_results SET moved_at_new = :val WHERE game_id = :gid"),
                {"val": dt, "gid": gid},
            )

    # NOTE: This draft does not drop old columns or rename the new columns into place.
    # Manual verification is recommended before performing destructive renames/drops.


def downgrade():
    # Remove the *_new columns added above
    with op.batch_alter_table('games_upcoming') as batch_op:
        batch_op.drop_column('scraped_at_new')

    with op.batch_alter_table('games_live') as batch_op:
        batch_op.drop_column('updated_at_new')

    with op.batch_alter_table('games_results') as batch_op:
        batch_op.drop_column('moved_at_new')
