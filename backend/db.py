"""Database configuration and session management."""
from contextlib import asynccontextmanager
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

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={
        "server_settings": {"statement_timeout": "60000"},  # 60s timeout for long queries
    },
)

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

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session