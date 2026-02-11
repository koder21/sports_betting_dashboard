import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime
from backend.models.games_live import GameLive
from backend.models.game import Game
from backend.config import settings

async def check_games():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Check GameResult for yesterday
        from backend.models.games_results import GameResult
        results = await session.execute(
            select(GameResult).where(
                GameResult.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                GameResult.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
        )
        game_results = results.scalars().all()
        print(f"GameResult records from yesterday: {len(game_results)}")
        for gr in game_results:
            print(f"  - {gr.away_team_name} @ {gr.home_team_name} | {gr.start_time}")
        
        # Check GameLive join with Game for yesterday
        live_with_start = await session.execute(
            select(GameLive, Game.start_time)
            .join(Game, GameLive.game_id == Game.game_id)
            .where(
                Game.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                Game.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
        )
        live_yesterday = live_with_start.all()
        print(f"\nGameLive records from yesterday (via Game join): {len(live_yesterday)}")
        for gl, st in live_yesterday:
            print(f"  - {gl.away_team_name} @ {gl.home_team_name} | {st}")

asyncio.run(check_games())
