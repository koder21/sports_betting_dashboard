import asyncio
from backend.db import get_session

async def check_stats(game_id):
    async with get_session() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("""
            SELECT COUNT(*) FROM player_stats WHERE game_id = :game_id
            """),
            {"game_id": game_id}
        )
        count = result.scalar()
        print(f"Player stats for game {game_id}: {count}")

if __name__ == "__main__":
    asyncio.run(check_stats('401810631'))
