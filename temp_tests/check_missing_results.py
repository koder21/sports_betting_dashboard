import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime
from backend.models.games_live import GameLive
from backend.models.games_results import GameResult
from backend.config import settings

async def check_games():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Get games from yesterday that are final
        from backend.models.game import Game
        
        all_live = await session.execute(
            select(GameLive)
            .join(Game, GameLive.game_id == Game.game_id)
            .where(
                Game.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                Game.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
            .order_by(Game.start_time)
        )
        live_games = all_live.scalars().all()
        
        # Get game IDs from GameResult
        results_query = await session.execute(
            select(GameResult).where(
                GameResult.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                GameResult.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
        )
        results = results_query.scalars().all()
        result_ids = {r.game_id for r in results}
        
        print(f"Games in GameResult: {len(results)}")
        print(f"Games in GameLive (from yesterday): {len(live_games)}")
        print()
        
        # Check the games that are in GameLive but not in GameResult
        missing_in_result = []
        for live in live_games:
            if live.game_id not in result_ids:
                missing_in_result.append(live)
        
        print(f"Games in GameLive but NOT in GameResult: {len(missing_in_result)}")
        print()
        
        for game in missing_in_result:
            print(f"Game ID: {game.game_id}")
            print(f"  Matchup: {game.away_team_name} @ {game.home_team_name}")
            print(f"  Score: {game.away_score} - {game.home_score}")
            print(f"  Status: {game.status}")
            print(f"  Has scores: {game.away_score is not None and game.home_score is not None}")
            print()

asyncio.run(check_games())
