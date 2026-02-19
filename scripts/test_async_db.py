import asyncio
from backend.db import get_session
from backend.models.games_results import GameResult

async def test_async_db():
    async with get_session() as session:
        result = await session.execute(
            GameResult.__table__.select().limit(1)
        )
        row = result.first()
        print("Test async DB query result:", row)

if __name__ == "__main__":
    asyncio.run(test_async_db())
