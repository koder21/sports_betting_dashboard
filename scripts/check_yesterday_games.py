import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime
from backend.models.games_results import GameResult
from backend.models.games_live import GameLive
from backend.models.game import Game
from backend.config import settings

async def check_games():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Check GameResult for yesterday
        results = await session.execute(
            select(GameResult).where(
                GameResult.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                GameResult.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
        )
        game_results = results.scalars().all()
        print(f"GameResult records from yesterday UTC: {len(game_results)}")
        for gr in game_results:
            print(f"  - {gr.home_team_name} vs {gr.away_team_name} | {gr.start_time}")
        
        # Count from GameLive that are from yesterday by joining with Game
        live_with_start = await session.execute(
            select(GameLive, Game.start_time)
            .join(Game, GameLive.game_id == Game.game_id)
            .where(
                Game.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                Game.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
        )
        live_yesterday = live_with_start.all()
        print(f"\nGameLive records from yesterday UTC (via Game join): {len(live_yesterday)}")
        for gl, st in live_yesterday:
            print(f"  - Game ID: {gl.game_id} | Start: {st}")
        
        # Show all games regardless of date (total count)
        all_games = await session.execute(select(Game))
        total_games = len(all_games.scalars().all())
        print(f"\nTotal games in Game table: {total_games}")

asyncio.run(check_games())
