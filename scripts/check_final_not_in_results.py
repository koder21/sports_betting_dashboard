import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models.games_live import GameLive
from backend.models.games_results import GameResult
from backend.models.game import Game
from backend.config import settings

async def check_games():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Get all games from GameLive
        all_live_query = await session.execute(select(GameLive))
        all_live = all_live_query.scalars().all()
        
        # Get all GameResult games
        all_results_query = await session.execute(select(GameResult))
        all_results = all_results_query.scalars().all()
        result_ids = {r.game_id for r in all_results}
        
        # Find games that are Final in GameLive but not in GameResult
        final_but_not_in_results = []
        for live in all_live:
            status_detail = live.status or ""
            if "Final" in status_detail or "FT" in status_detail:
                if live.game_id not in result_ids:
                    final_but_not_in_results.append(live)
        
        print(f"Total GameLive records: {len(all_live)}")
        print(f"Total GameResult records: {len(all_results)}")
        print(f"Final games in GameLive NOT in GameResult: {len(final_but_not_in_results)}")
        print()
        
        # Get their start times
        for live in final_but_not_in_results[:15]:  # Show first 15
            game_q = await session.execute(
                select(Game).where(Game.game_id == live.game_id)
            )
            game = game_q.scalar()
            start_time = game.start_time if game else "N/A"
            print(f"Game ID: {live.game_id}")
            print(f"  Matchup: {live.away_team_name} @ {live.home_team_name}")
            print(f"  Score: {live.away_score} - {live.home_score}")
            print(f"  Status: {live.status}")
            print(f"  Start Time (from Game): {start_time}")
            print()

asyncio.run(check_games())
