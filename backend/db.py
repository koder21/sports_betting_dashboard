"""Database configuration and session management."""
from contextlib import asynccontextmanager
import logging
import os
import subprocess
import sys
from typing import AsyncGenerator

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import settings
from .models.base import Base

from .models import (  # noqa: F401
    Sport, Team, Player, Game, PlayerStat, Bet, Alert, Injury, Standing,
)
from .models.games_upcoming import GameUpcoming  # noqa: F401
from .models.games_live import GameLive  # noqa: F401
from .models.games_results import GameResult  # noqa: F401
from .models.player_stats import PlayerStats  # noqa: F401

logger = logging.getLogger(__name__)

_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            poolclass=NullPool,
            connect_args={
                "server_settings": {"statement_timeout": "60000"},
            },
        )
    return _engine


def _get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _AsyncSessionLocal


# Proxy so existing code using `engine` and `AsyncSessionLocal` still works
class _EngineProxy:
    def __getattr__(self, name):
        return getattr(_get_engine(), name)
    def begin(self):
        return _get_engine().begin()

class _SessionFactoryProxy:
    def __call__(self, *args, **kwargs):
        return _get_session_factory()(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(_get_session_factory(), name)

engine = _EngineProxy()
AsyncSessionLocal = _SessionFactoryProxy()


async def init_db() -> None:  # noqa: C901
    """Initialize the database safely for both fresh and existing deployments.

    Strategy
    --------
    Two modes are detected at runtime by checking for an ``alembic_version`` row:

    **Fresh database** (no ``alembic_version`` row — brand-new Railway Postgres):
      1. ``Base.metadata.create_all(checkfirst=True)`` — creates every table,
         column, index, and constraint directly from the SQLAlchemy models.
      2. ``alembic stamp head`` — tells Alembic the DB is already at the latest
         revision so future deploys only apply new deltas.

    **Existing managed database** (has ``alembic_version`` row):
      1. ``alembic upgrade head`` — applies any pending migrations.
      2. ``create_all(checkfirst=True)`` safety net for any new models not yet
         covered by a migration.

    Why not always run ``alembic upgrade head``?
    The existing migrations are all ALTER-type — rename columns, drop tables,
    add indexes.  On a brand-new empty database they crash immediately because
    the tables they're altering don't exist yet.  The ``create_all`` path
    produces the correct final schema directly from the models and ``stamp head``
    ensures subsequent deploys stay migration-managed.
    """
    from sqlalchemy import text as sa_text

    engine = _get_engine()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ── Step 1: Detect fresh vs existing ─────────────────────────────────────
    is_fresh = True
    try:
        async with engine.connect() as conn:
            result = await conn.execute(sa_text("SELECT 1 FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            # Table exists — if no row, DB was created but never stamped; treat as fresh
            is_fresh = (row is None)
    except Exception:
        # alembic_version table doesn't exist at all → definitely fresh
        is_fresh = True

    if is_fresh:
        # ── Path A: Fresh DB — create schema from models, then stamp ──────────
        logger.info("Fresh database detected — building schema from models")
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
        logger.info("All tables created from SQLAlchemy models")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "stamp", "head"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                logger.info("alembic stamp stdout: %s", result.stdout.strip())
            if result.stderr:
                logger.info("alembic stamp stderr: %s", result.stderr.strip())
            if result.returncode == 0:
                logger.info("alembic stamp head complete — future deploys will use migrations")
            else:
                logger.warning("alembic stamp head failed (rc=%d) — not fatal", result.returncode)
        except Exception as exc:
            logger.warning("Could not run alembic stamp head: %s — not fatal", exc)

    else:
        # ── Path B: Existing managed DB — run pending migrations ──────────────
        logger.info("Existing database detected — running alembic upgrade head")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                logger.info("alembic stdout: %s", result.stdout.strip())
            if result.stderr:
                logger.info("alembic stderr: %s", result.stderr.strip())
            if result.returncode != 0:
                logger.error("alembic upgrade head failed (rc=%d)", result.returncode)
            else:
                logger.info("alembic upgrade head completed successfully")
        except Exception as exc:
            logger.error("Could not run alembic upgrade head: %s", exc)

        # Safety net: create any new model tables not yet covered by migrations
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session
