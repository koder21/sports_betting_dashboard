from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timedelta

from ..db import get_session
from ..models import GameLive, Game, GameUpcoming, GameResult

router = APIRouter()

SPORTS = {
    1: "NBA",
    2: "NFL",
    3: "NHL",
    4: "NCAAB",
    5: "EPL",
}

async def _get_live_scores(session: AsyncSession):
    """Fetch live games from the database with start times from games table.
    
    OPTIMIZED: Fetch all GameLive records along with GameUpcoming and GameResult
    in bulk queries to avoid N+1 query problem.
    """
    # Fetch all live games
    live_result = await session.execute(select(GameLive))
    live_games = live_result.scalars().all()
    
    if not live_games:
        return []
    
    # Extract all game IDs for bulk lookup
    game_ids = [game.game_id for game in live_games]
    
    # Bulk fetch all related records in one query each
    upcoming_result = await session.execute(
        select(GameUpcoming).where(GameUpcoming.game_id.in_(game_ids))
    )
    upcoming_records = {r.game_id: r for r in upcoming_result.scalars()}
    
    result_result = await session.execute(
        select(GameResult).where(GameResult.game_id.in_(game_ids))
    )
    result_records = {r.game_id: r for r in result_result.scalars()}
    
    games_result = await session.execute(
        select(Game).where(Game.game_id.in_(game_ids))
    )
    game_records = {g.game_id: g for g in games_result.scalars()}
    
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
        
        # Get start time and logos from pre-fetched records (no queries in loop)
        start_time = None
        home_logo = None
        away_logo = None
        
        # Check GameUpcoming first since scheduler updates it with fresh times
        upcoming_record = upcoming_records.get(game.game_id)
        if upcoming_record:
            if upcoming_record.start_time:
                start_time = upcoming_record.start_time
            home_logo = upcoming_record.home_logo
            away_logo = upcoming_record.away_logo
        
        # Fallback to GameResult for finished games
        if not home_logo or not away_logo:
            result_record = result_records.get(game.game_id)
            if result_record:
                if not home_logo:
                    home_logo = result_record.home_logo
                if not away_logo:
                    away_logo = result_record.away_logo
        
        # Fallback to games table if no start time yet
        if not start_time:
            game_record = game_records.get(game.game_id)
            if game_record and game_record.start_time:
                start_time = game_record.start_time
        
        # Last resort: try GameLive itself if it has start_time
        if not start_time and hasattr(game, 'start_time') and game.start_time:
            start_time = game.start_time
        
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
            if isinstance(start_time, str):
                game_dict["start_time"] = start_time
            elif hasattr(start_time, 'isoformat'):
                game_dict["start_time"] = start_time.isoformat()
            else:
                game_dict["start_time"] = str(start_time)
        
        # Add optional fields if they exist
        if game.period is not None:
            game_dict["period"] = game.period
        if game.clock is not None:
            game_dict["clock"] = game.clock
        if game.possession is not None:
            game_dict["possession"] = game.possession
        if home_logo:
            game_dict["home_logo"] = home_logo
        if away_logo:
            game_dict["away_logo"] = away_logo
        
        games_list.append(game_dict)
    
    return games_list

@router.get("")
@router.get("/")
async def get_live_scores(session: AsyncSession = Depends(get_session)):
    """Fetch live games from the database."""
    return await _get_live_scores(session)