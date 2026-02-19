import asyncio
from backend.db import get_session
from backend.models.player_stats import PlayerStats
from sqlalchemy import select

async def main():
    game_id = str(401810631)
    async with get_session() as session:
        result = await session.execute(select(PlayerStats).where(PlayerStats.game_id == game_id))
        stats = result.fetchall()
        print(f"Player stats for game {game_id}: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
