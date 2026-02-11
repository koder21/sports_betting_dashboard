"""
Sync snapshot tables (games_upcoming, games_live, games_results) from games table.
Based on game status and start_time.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.models import Game, GameUpcoming, GameLive, GameResult, Sport
from backend.models.base import Base


async def sync_snapshots():
    """Populate snapshot tables from games table."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Fetch all games
        result = await session.execute(select(Game))
        games = result.scalars().all()
        
        print(f"Found {len(games)} games to process...")
        
        upcoming_count = 0
        live_count = 0
        results_count = 0
        
        now = datetime.utcnow()
        
        # OPTIMIZATION: Bulk fetch all snapshot records at once instead of checking per game (Nx speedup)
        import asyncio
        game_ids = [g.game_id for g in games if g.game_id]
        
        if game_ids:
            upcoming_batch, live_batch, results_batch = await asyncio.gather(
                session.execute(select(GameUpcoming.game_id).where(GameUpcoming.game_id.in_(game_ids))),
                session.execute(select(GameLive.game_id).where(GameLive.game_id.in_(game_ids))),
                session.execute(select(GameResult.game_id).where(GameResult.game_id.in_(game_ids))),
                return_exceptions=False
            )
            existing_upcoming = {r[0] for r in upcoming_batch.all()}
            existing_live = {r[0] for r in live_batch.all()}
            existing_results = {r[0] for r in results_batch.all()}
        else:
            existing_upcoming = existing_live = existing_results = set()
        
        for game in games:
            status = (game.status or "").upper()
            start_time = game.start_time
            
            # Determine which snapshot table this game belongs to
            if not start_time:
                print(f"  Game {game.game_id} has no start_time, skipping")
                continue
            
            # Check if game already in any snapshot table
            if game.game_id in existing_upcoming or game.game_id in existing_live or game.game_id in existing_results:
                continue
            
            # Get sport from sport_id if available, otherwise look for it from game.sport field
            sport_name = "Unknown"
            if game.sport_id:
                sport_result = await session.execute(
                    select(Sport).where(Sport.id == game.sport_id)
                )
                sport = sport_result.scalar()
                if sport:
                    sport_name = sport.name
            elif game.sport:
                sport_name = game.sport
            
            # Determine correct snapshot table
            if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                # Game is finished
                snapshot = GameResult(
                    game_id=game.game_id,
                    start_time=start_time,
                    end_time=now,
                    home_score=0,
                    away_score=0,
                    status=status,
                )
                session.add(snapshot)
                results_count += 1
            elif status in ("STATUS_IN_PROGRESS", "STATUS_LIVE", "STATUS_HALFTIME"):
                # Game is live or at halftime - copy to GameLive
                snapshot = GameLive(
                    game_id=game.game_id,
                    sport=sport_name,
                    home_team_name=game.home_team_name or "Home Team",
                    away_team_name=game.away_team_name or "Away Team",
                    home_score=game.home_score or 0,
                    away_score=game.away_score or 0,
                    period=game.period,
                    clock=game.clock,
                    status=status,
                    updated_at=now,
                )
                session.add(snapshot)
                live_count += 1
            else:
                # Game is upcoming - fetch logos from GameResult if available
                home_logo = None
                away_logo = None
                
                # Try to get logos from GameResult table
                result_check = await session.execute(
                    select(GameResult).where(GameResult.game_id == game.game_id)
                )
                result_record = result_check.scalar()
                if result_record:
                    home_logo = result_record.home_logo
                    away_logo = result_record.away_logo
                
                snapshot = GameUpcoming(
                    game_id=game.game_id,
                    start_time=start_time,
                    sport=sport_name,
                    home_team_name=game.home_team_name or None,
                    away_team_name=game.away_team_name or None,
                    status=game.status,
                    home_logo=home_logo,
                    away_logo=away_logo,
                )
                session.add(snapshot)
                upcoming_count += 1
        
        # Commit all changes
        await session.commit()
        
        print(f"\nSnapshot sync complete:")
        print(f"  games_upcoming: {upcoming_count}")
        print(f"  games_live: {live_count}")
        print(f"  games_results: {results_count}")


if __name__ == "__main__":
    asyncio.run(sync_snapshots())
