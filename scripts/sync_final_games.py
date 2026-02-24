import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime
from backend.models.games_live import GameLive
from backend.models.games_results import GameResult
from backend.models.game import Game
from backend.config import settings

async def sync_games():
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
        
        print(f"Found {len(final_but_not_in_results)} final games in GameLive not in GameResult")
        print()
        
        # Create GameResult entries for these games
        created_count = 0
        for live in final_but_not_in_results:
            # Get the start_time from Game table
            game_q = await session.execute(
                select(Game).where(Game.game_id == live.game_id)
            )
            game = game_q.scalar()
            
            if not game:
                print(f"Warning: Game {live.game_id} not found in Game table")
                continue
            
            # Create GameResult entry
            game_result = GameResult(
                game_id=live.game_id,
                sport=live.sport,
                league=game.league,
                start_time=game.start_time,
                status=live.status,
                home_team_id=live.home_team_id if hasattr(live, 'home_team_id') else None,
                home_team_name=live.home_team_name,
                away_team_id=live.away_team_id if hasattr(live, 'away_team_id') else None,
                away_team_name=live.away_team_name,
                home_score=live.home_score,
                away_score=live.away_score,
            )
            session.add(game_result)
            created_count += 1
            print(f"Created GameResult for {live.away_team_name} @ {live.home_team_name}")
        
        if created_count > 0:
            await session.commit()
            print(f"\n✅ Successfully created {created_count} GameResult entries")
        else:
            print("\nNo games to sync")

asyncio.run(sync_games())
