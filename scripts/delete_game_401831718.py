import asyncio
from backend.db import get_session
from backend.models.games_results import GameResult

async def delete_game(game_id: str):
    async with get_session() as session:
        await session.execute(
            GameResult.__table__.delete().where(GameResult.game_id == game_id)
        )
        await session.commit()
        print(f"Deleted game_id {game_id} from games_results.")

if __name__ == "__main__":
    asyncio.run(delete_game("401831718"))
