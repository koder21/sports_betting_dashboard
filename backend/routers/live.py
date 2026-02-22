from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timedelta

from ..db import get_db
from ..models import GameLive, Game, GameUpcoming, GameResult

router = APIRouter()

# Add upcoming endpoint after router is defined
@router.get("/upcoming")
async def get_upcoming_games(session: AsyncSession = Depends(get_db)):
    """Always fetch all upcoming/scheduled games from the database."""
    now = datetime.utcnow()
    upcoming_result = await session.execute(select(GameUpcoming))
    upcoming_games = upcoming_result.scalars().all()
    games_list = []
    for game in upcoming_games:
        start_time = game.start_time if hasattr(game, 'start_time') else None
        parsed_start = None
        if start_time:
            if isinstance(start_time, str):
                try:
                    parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except Exception:
                    parsed_start = None
            elif hasattr(start_time, 'isoformat'):
                parsed_start = start_time
        # Only include games that are scheduled or have a start_time in the future
        if (parsed_start and parsed_start > now) or (getattr(game, 'status', None) == 'scheduled'):
            game_dict = {
                "game_id": game.game_id,
                "home_score": getattr(game, 'home_score', 0) or 0,
                "away_score": getattr(game, 'away_score', 0) or 0,
                "home_team": getattr(game, 'home_team_name', None) or getattr(game, 'home_team', None) or "Home Team",
                "away_team": getattr(game, 'away_team_name', None) or getattr(game, 'away_team', None) or "Away Team",
                "home_team_id": getattr(game, 'home_team_id', None),
                "away_team_id": getattr(game, 'away_team_id', None),
                "status": getattr(game, 'status', 'scheduled'),
                "sport": (getattr(game, 'sport', None) or "Unknown").upper(),
            }
            if start_time:
                if isinstance(start_time, str):
                    game_dict["start_time"] = start_time
                elif hasattr(start_time, 'isoformat'):
                    game_dict["start_time"] = start_time.isoformat()
                else:
                    game_dict["start_time"] = str(start_time)
            if hasattr(game, 'period') and game.period is not None:
                game_dict["period"] = game.period
            if hasattr(game, 'clock') and game.clock is not None:
                game_dict["clock"] = game.clock
            if hasattr(game, 'possession') and game.possession is not None:
                game_dict["possession"] = game.possession
            if hasattr(game, 'home_logo') and game.home_logo:
                game_dict["home_logo"] = game.home_logo
            if hasattr(game, 'away_logo') and game.away_logo:
                game_dict["away_logo"] = game.away_logo
            games_list.append(game_dict)
    return games_list

SPORTS = {

    1: "NBA",
    2: "NFL",
    3: "NHL",
    4: "NCAAB",
    5: "NCAAF",
    6: "MLB",
    7: "EPL",
}

from .games import classify_game_status



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
    now = datetime.utcnow()
    for game in live_games:
        status = classify_game_status(game.status, game.clock, game.home_score, game.away_score)
        # Only show games that are ongoing (live) or completed (final)
        if status not in ("ongoing", "completed"):
            continue
        start_time = None
        home_logo = None
        away_logo = None
        upcoming_record = upcoming_records.get(game.game_id)
        if upcoming_record:
            if upcoming_record.start_time:
                start_time = upcoming_record.start_time
            home_logo = upcoming_record.home_logo
            away_logo = upcoming_record.away_logo
        if not home_logo or not away_logo:
            result_record = result_records.get(game.game_id)
            if result_record:
                if not home_logo:
                    home_logo = result_record.home_logo
                if not away_logo:
                    away_logo = result_record.away_logo
        if not start_time:
            game_record = game_records.get(game.game_id)
            if game_record and game_record.start_time:
                start_time = game_record.start_time
        if not start_time and hasattr(game, 'start_time') and game.start_time:
            start_time = game.start_time
        # Filter out games whose start_time is in the future (not yet started)
        parsed_start = None
        if start_time:
            if isinstance(start_time, str):
                try:
                    parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except Exception:
                    parsed_start = None
            elif hasattr(start_time, 'isoformat'):
                parsed_start = start_time
        if parsed_start and parsed_start > now and status != "completed":
            continue
        # Fetch team IDs from core Game record if available
        core_game = game_records.get(game.game_id)
        home_team_id = None
        away_team_id = None
        if core_game:
                home_team_id = getattr(core_game, 'home_team_id', None)
                away_team_id = getattr(core_game, 'away_team_id', None)
                # Patch: prepend sport prefix for all teams to match analytics
                sport = getattr(core_game, 'sport', None)
                if sport:
                    sport_prefix = sport.upper()
                    for prefix in ['NBA', 'NFL', 'NHL', 'NCAAB', 'NCAAF', 'MLB', 'EPL']:
                        if sport_prefix == prefix:
                            if home_team_id and not str(home_team_id).startswith(f'{prefix}-'):
                                home_team_id = f'{prefix}-{home_team_id}'
                            if away_team_id and not str(away_team_id).startswith(f'{prefix}-'):
                                away_team_id = f'{prefix}-{away_team_id}'
                            break
        game_dict = {
            "game_id": game.game_id,
            "home_score": game.home_score or 0,
            "away_score": game.away_score or 0,
            "home_team": game.home_team_name or "Home Team",
            "away_team": game.away_team_name or "Away Team",
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "status": status,
            "sport": (game.sport or "Unknown").upper(),
        }
        if start_time:
            if isinstance(start_time, str):
                game_dict["start_time"] = start_time
            elif hasattr(start_time, 'isoformat'):
                game_dict["start_time"] = start_time.isoformat()
            else:
                game_dict["start_time"] = str(start_time)
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
async def get_live_scores(session: AsyncSession = Depends(get_db)):
    """Fetch live games from the database."""
    return await _get_live_scores(session)