import asyncio
from backend.db import get_session
from backend.models.games_results import GameResult
from sqlalchemy import select

async def main():
    game_id = "401810631"
    async with get_session() as session:
        result = await session.execute(select(GameResult).where(GameResult.game_id == game_id))
        game = result.first()
        print(f"games_results row for game {game_id}: {game}")

if __name__ == "__main__":
    asyncio.run(main())
