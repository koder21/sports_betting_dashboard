from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, and_, case, extract
from typing import Dict, Any, List
from datetime import datetime, timedelta

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
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_games_result = await session.execute(
        select(func.count(distinct(GameResult.game_id)))
        .where(
            GameResult.sport == sport_upper,
            GameResult.start_time >= thirty_days_ago
        )
    )
    recent_games = recent_games_result.scalar() or 0
    
    # Get home vs away win statistics
    home_wins_result = await session.execute(
        select(func.count(GameResult.game_id))
        .where(
            GameResult.sport == sport_upper,
            GameResult.home_score > GameResult.away_score
        )
    )
    home_wins = home_wins_result.scalar() or 0
    
    away_wins_result = await session.execute(
        select(func.count(GameResult.game_id))
        .where(
            GameResult.sport == sport_upper,
            GameResult.away_score > GameResult.home_score
        )
    )
    away_wins = away_wins_result.scalar() or 0
    
    # Get scoring statistics
    avg_scores_result = await session.execute(
        select(
            func.avg(GameResult.home_score),
            func.avg(GameResult.away_score),
            func.avg(GameResult.home_score + GameResult.away_score)
        )
        .where(
            GameResult.sport == sport_upper,
            GameResult.home_score.is_not(None),
            GameResult.away_score.is_not(None)
        )
    )
    avg_scores = avg_scores_result.first()
    
    # Get games per month for the last 12 months
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    monthly_games_result = await session.execute(
        select(
            extract('year', GameResult.start_time).label('year'),
            extract('month', GameResult.start_time).label('month'),
            func.count(GameResult.game_id).label('count')
        )
        .where(
            GameResult.sport == sport_upper,
            GameResult.start_time >= twelve_months_ago,
            GameResult.start_time.is_not(None)
        )
        .group_by('year', 'month')
        .order_by('year', 'month')
    )
    monthly_games = [{"month": f"{int(row.year)}-{int(row.month):02d}", "games": row.count} for row in monthly_games_result.all()]
    
    # Get top scoring teams (last 30 days)
    top_teams_result = await session.execute(
        select(
            GameResult.home_team_name.label('team'),
            func.avg(GameResult.home_score).label('avg_score')
        )
        .where(
            GameResult.sport == sport_upper,
            GameResult.start_time >= thirty_days_ago,
            GameResult.home_team_name.is_not(None),
            GameResult.home_score.is_not(None)
        )
        .group_by('team')
        .order_by(func.avg(GameResult.home_score).desc())
        .limit(10)
    )
    top_teams = [{"team": row.team, "avg_score": round(row.avg_score, 1)} for row in top_teams_result.all()]
    
    # Calculate scoring distribution (bins for histogram)
    score_distribution_result = await session.execute(
        select(
            case(
                (GameResult.home_score + GameResult.away_score < 200, '0-199'),
                (GameResult.home_score + GameResult.away_score < 210, '200-209'),
                (GameResult.home_score + GameResult.away_score < 220, '210-219'),
                (GameResult.home_score + GameResult.away_score < 230, '220-229'),
                (GameResult.home_score + GameResult.away_score < 240, '230-239'),
                else_='240+'
            ).label('range'),
            func.count(GameResult.game_id).label('count')
        )
        .where(
            GameResult.sport == sport_upper,
            GameResult.home_score.is_not(None),
            GameResult.away_score.is_not(None),
            GameResult.start_time >= thirty_days_ago
        )
        .group_by('range')
    )
    score_distribution = [{"range": row.range, "count": row.count} for row in score_distribution_result.all()]
    
    return {
        "sport": sport_upper,
        "total_games": total_games,
        "total_players": total_players,
        "total_stats": total_stats,
        "total_teams": total_teams,
        "recent_games_30d": recent_games,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "avg_home_score": round(avg_scores[0], 1) if avg_scores[0] else 0,
        "avg_away_score": round(avg_scores[1], 1) if avg_scores[1] else 0,
        "avg_total_score": round(avg_scores[2], 1) if avg_scores[2] else 0,
        "monthly_games": monthly_games,
        "top_teams": top_teams,
        "score_distribution": score_distribution
    }


@router.get("/overview")
async def get_sports_overview(session: AsyncSession = Depends(get_session)):
    """Get comparative overview statistics for all sports"""
    
    sports = ["NBA", "NFL", "NCAAB", "NHL", "EPL"]
    
    # Collect data for each sport
    sport_comparisons = []
    total_games_all = 0
    total_players_all = 0
    
    for sport_code in sports:
        # Get total games
        games_result = await session.execute(
            select(func.count(distinct(GameResult.game_id)))
            .where(GameResult.sport == sport_code)
        )
        total_games = games_result.scalar() or 0
        total_games_all += total_games
        
        # Get total players
        players_result = await session.execute(
            select(func.count(distinct(Player.player_id)))
            .where(Player.sport == sport_code)
        )
        total_players = players_result.scalar() or 0
        total_players_all += total_players
        
        # Get total teams
        teams_result = await session.execute(
            select(func.count(distinct(Team.team_id)))
            .where(Team.sport_name == sport_code)
        )
        total_teams = teams_result.scalar() or 0
        
        # Get recent games (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_games_result = await session.execute(
            select(func.count(distinct(GameResult.game_id)))
            .where(
                GameResult.sport == sport_code,
                GameResult.start_time >= thirty_days_ago
            )
        )
        recent_games = recent_games_result.scalar() or 0
        
        # Get average total score
        avg_score_result = await session.execute(
            select(func.avg(GameResult.home_score + GameResult.away_score))
            .where(
                GameResult.sport == sport_code,
                GameResult.home_score.is_not(None),
                GameResult.away_score.is_not(None)
            )
        )
        avg_total_score = avg_score_result.scalar() or 0
        
        # Get home win percentage
        home_wins_result = await session.execute(
            select(func.count(GameResult.game_id))
            .where(
                GameResult.sport == sport_code,
                GameResult.home_score > GameResult.away_score
            )
        )
        home_wins = home_wins_result.scalar() or 0
        home_win_pct = (home_wins / total_games * 100) if total_games > 0 else 0
        
        sport_comparisons.append({
            "sport": sport_code,
            "total_games": total_games,
            "total_players": total_players,
            "total_teams": total_teams,
            "recent_games_30d": recent_games,
            "avg_total_score": round(avg_total_score, 1),
            "home_win_percentage": round(home_win_pct, 1)
        })
    
    # Get monthly trend for all sports combined
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    monthly_all_sports = {}
    
    for sport_code in sports:
        monthly_result = await session.execute(
            select(
                extract('year', GameResult.start_time).label('year'),
                extract('month', GameResult.start_time).label('month'),
                func.count(GameResult.game_id).label('count')
            )
            .where(
                GameResult.sport == sport_code,
                GameResult.start_time >= twelve_months_ago,
                GameResult.start_time.is_not(None)
            )
            .group_by('year', 'month')
            .order_by('year', 'month')
        )
        
        for row in monthly_result.all():
            month_key = f"{int(row.year)}-{int(row.month):02d}"
            if month_key not in monthly_all_sports:
                monthly_all_sports[month_key] = {"month": month_key}
            monthly_all_sports[month_key][sport_code] = row.count
    
    # Fill in missing months with 0
    monthly_trend = []
    for month_key in sorted(monthly_all_sports.keys()):
        month_data = monthly_all_sports[month_key]
        for sport_code in sports:
            if sport_code not in month_data:
                month_data[sport_code] = 0
        monthly_trend.append(month_data)
    
    return {
        "sports_comparison": sport_comparisons,
        "monthly_trend": monthly_trend,
        "total_games": total_games_all,
        "total_players": total_players_all,
        "sports_count": len(sports)
    }
