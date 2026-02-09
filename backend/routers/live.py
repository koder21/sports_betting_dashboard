from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timedelta

from ..db import get_session
from ..models import GameLive, Game, GameUpcoming

router = APIRouter()

SPORTS = {
    1: "NBA",
    2: "NFL",
    3: "NHL",
    4: "NCAAB",
    5: "EPL",
}

async def _get_live_scores(session: AsyncSession):
    """Fetch live games from the database with start times from games table."""
    result = await session.execute(select(GameLive))
    live_games = result.scalars().all()
    
    games_list = []
    for game in live_games:
        # Determine status based on the status field from ESPN
        status_detail = game.status or ""
        
        # Check status_detail first (ESPN is the source of truth)
        # Final statuses
        if "Final" in status_detail or "FT" in status_detail or status_detail == "Full Time":
            status = "final"
        # Game is in progress - check for various live game indicators
        elif any(indicator in status_detail for indicator in ["In Progress", "Halftime", "HT", "1st", "2nd", "3rd", "4th", "OT", "1H", "2H"]) or "'" in status_detail:
            status = "in"
        # Additional check: if has clock and any scores, it's likely live
        elif game.clock and game.clock.strip() and (game.home_score or 0) + (game.away_score or 0) > 0:
            status = "in"
        # Default to scheduled for everything else
        else:
            status = "scheduled"
        
        # Get start time - check GameUpcoming first (freshest data), then Game table
        start_time = None
        try:
            # Try GameUpcoming first since scheduler updates it with fresh times
            upcoming_result = await session.execute(
                select(GameUpcoming).where(GameUpcoming.game_id == game.game_id)
            )
            upcoming_record = upcoming_result.scalar()
            if upcoming_record and upcoming_record.start_time:
                start_time = upcoming_record.start_time
            
            # Fallback to games table if not in GameUpcoming
            if not start_time:
                games_result = await session.execute(
                    select(Game).where(Game.game_id == game.game_id)
                )
                game_record = games_result.scalar()
                if game_record and game_record.start_time:
                    start_time = game_record.start_time
            
            # Last resort: try GameLive itself if it has start_time
            if not start_time and hasattr(game, 'start_time') and game.start_time:
                start_time = game.start_time
        except:
            pass
        
        game_dict = {
            "game_id": game.game_id,
            "home_score": game.home_score or 0,
            "away_score": game.away_score or 0,
            "home_team": game.home_team_name or "Home Team",
            "away_team": game.away_team_name or "Away Team",
            "status": status,
            "sport": (game.sport or "Unknown").upper(),
        }
        
        # Return start time as ISO string for frontend timezone conversion
        if start_time:
            try:
                if isinstance(start_time, str):
                    game_dict["start_time"] = start_time
                else:
                    # Convert datetime to ISO format string
                    game_dict["start_time"] = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
            except:
                pass
        
        # Add optional fields if they exist
        if game.period is not None:
            game_dict["period"] = game.period
        if game.clock is not None:
            game_dict["clock"] = game.clock
        if game.possession is not None:
            game_dict["possession"] = game.possession
        
        games_list.append(game_dict)
    
    return games_list

@router.get("")
@router.get("/")
async def get_live_scores(session: AsyncSession = Depends(get_session)):
    """Fetch live games from the database."""
    return await _get_live_scores(session)