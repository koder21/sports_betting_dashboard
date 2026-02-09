from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from .config import settings
from .models.base import Base
# Import all models so Base.metadata has every table (for create_all in init_db)
from .models import (  # noqa: F401
    Sport, Team, Player, Game, PlayerStat, Bet, Alert, Injury, Standing,
)
# Import game state models (GameUpcoming, GameLive, GameResult)
from .models.games_upcoming import GameUpcoming  # noqa: F401
from .models.games_live import GameLive  # noqa: F401
from .models.games_results import GameResult  # noqa: F401
from .models.player_stats import PlayerStats  # noqa: F401

# Enable WAL mode for SQLite to allow concurrent reads/writes
# Also increase timeout and use NullPool to avoid connection issues
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,  # No connection pooling for SQLite
    connect_args={
        "timeout": 30,  # Increase timeout for locked database
        "check_same_thread": False,
    }
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and other SQLite optimizations"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session