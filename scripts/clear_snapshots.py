"""Clear and re-sync snapshot tables with actual data from games table."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.models import GameUpcoming, GameLive, GameResult


async def clear_snapshots():
    """Clear all snapshot tables."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Delete all rows
        await session.execute(delete(GameUpcoming))
        await session.execute(delete(GameLive))
        await session.execute(delete(GameResult))
        await session.commit()
        print("✓ Cleared all snapshot tables")


if __name__ == "__main__":
    asyncio.run(clear_snapshots())
