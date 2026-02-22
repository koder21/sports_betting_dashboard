"""Database configuration and session management."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import settings
from .models.base import Base

# Import all models so Base.metadata includes all tables
from .models import (  # noqa: F401
    Sport, Team, Player, Game, PlayerStat, Bet, Alert, Injury, Standing,
)
from .models.games_upcoming import GameUpcoming  # noqa: F401
from .models.games_live import GameLive  # noqa: F401
from .models.games_results import GameResult  # noqa: F401
from .models.player_stats import PlayerStats  # noqa: F401


# Async engine with NullPool to avoid connection pool issues with asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={
        "server_settings": {"statement_timeout": "60000"},  # 60s timeout for long queries
    },
)

# Session factory with explicit transaction control
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """Initialize database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Ensure MLB and EPL are present in the sports table
    async with AsyncSessionLocal() as session:
        from .models.sport import Sport
        from sqlalchemy.dialects.postgresql import insert
        sports_to_insert = [
            {"name": "MLB", "espn_league_code": "mlb", "league": "MLB"},
            {"name": "EPL", "espn_league_code": "epl", "league": "EPL"},
        ]
        for sport in sports_to_insert:
            stmt = insert(Sport).values(**sport).on_conflict_do_nothing(index_elements=["name"])
            await session.execute(stmt)
        await session.commit()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Usage:
        async with get_session() as session:
            # Use session here
            pass  # Automatically commits on success, rolls back on error
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# FastAPI dependency - alias for consistency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage in routes:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
    """
    async with get_session() as session:
        yield session