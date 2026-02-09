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
        
        for game in games:
            status = (game.status or "").upper()
            start_time = game.start_time
            
            # Determine which snapshot table this game belongs to
            if not start_time:
                print(f"  Game {game.game_id} has no start_time, skipping")
                continue
            
            # Check if game already in any snapshot table
            upcoming_exists = await session.execute(
                select(GameUpcoming).where(GameUpcoming.game_id == game.game_id)
            )
            live_exists = await session.execute(
                select(GameLive).where(GameLive.game_id == game.game_id)
            )
            results_exists = await session.execute(
                select(GameResult).where(GameResult.game_id == game.game_id)
            )
            
            if upcoming_exists.scalars().first() or live_exists.scalars().first() or results_exists.scalars().first():
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
                # Game is upcoming
                snapshot = GameUpcoming(
                    game_id=game.game_id,
                    start_time=start_time,
                    sport=sport_name,
                    home_team_name=game.home_team_name or None,
                    away_team_name=game.away_team_name or None,
                    status=game.status,
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
