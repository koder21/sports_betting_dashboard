from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from typing import Dict, Any

from ..db import get_session
from ..models.games_results import GameResult
from ..models.player import Player
from ..models.player_stats import PlayerStats
from ..models.team import Team

router = APIRouter()


@router.get("/stats/{sport}")
async def get_sport_stats(sport: str, session: AsyncSession = Depends(get_session)):
    """Get statistics for a specific sport"""
    sport_upper = sport.upper()
    
    # Count completed games
    games_result = await session.execute(
        select(func.count(distinct(GameResult.game_id)))
        .where(GameResult.sport == sport_upper)
    )
    total_games = games_result.scalar() or 0
    
    # Count players
    players_result = await session.execute(
        select(func.count(distinct(Player.player_id)))
        .where(Player.sport == sport_upper)
    )
    total_players = players_result.scalar() or 0
    
    # Count player stats records
    stats_result = await session.execute(
        select(func.count(PlayerStats.id))
        .where(PlayerStats.sport == sport_upper)
    )
    total_stats = stats_result.scalar() or 0
    
    # Count teams
    teams_result = await session.execute(
        select(func.count(distinct(Team.team_id)))
        .where(Team.sport_name == sport_upper)
    )
    total_teams = teams_result.scalar() or 0
    
    # Get recent games (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_games_result = await session.execute(
        select(func.count(distinct(GameResult.game_id)))
        .where(
            GameResult.sport == sport_upper,
            GameResult.start_time >= thirty_days_ago
        )
    )
    recent_games = recent_games_result.scalar() or 0
    
    return {
        "sport": sport_upper,
        "total_games": total_games,
        "total_players": total_players,
        "total_stats": total_stats,
        "total_teams": total_teams,
        "recent_games_30d": recent_games,
    }


@router.get("/overview")
async def get_sports_overview(session: AsyncSession = Depends(get_session)):
    """Get overview statistics for all sports"""
    
    # Get all sports from the database
    sports = ["NBA", "NFL", "NCAAB", "NHL", "EPL"]
    
    overview = {}
    for sport in sports:
        sport_data = await get_sport_stats(sport, session)
        overview[sport] = sport_data
    
    return overview
