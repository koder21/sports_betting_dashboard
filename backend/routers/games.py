from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict
from zoneinfo import ZoneInfo

from ..db import get_session
from ..services.intelligence.game_intel import GameIntelligenceService
from ..models.games_results import GameResult
from ..models.games_upcoming import GameUpcoming

router = APIRouter()


@router.get("/ai-context")
async def get_ai_context(session: AsyncSession = Depends(get_session)):
    """Get yesterday's results and today's upcoming games for AI analysis"""
    # Use PST timezone for date calculations
    pst = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst)
    today_pst = now_pst.date()
    yesterday_pst = today_pst - timedelta(days=1)
    
    # Convert PST dates to UTC for database queries
    yesterday_start_pst = datetime.combine(yesterday_pst, datetime.min.time()).replace(tzinfo=pst)
    today_start_pst = datetime.combine(today_pst, datetime.min.time()).replace(tzinfo=pst)
    tomorrow_start_pst = datetime.combine(today_pst + timedelta(days=1), datetime.min.time()).replace(tzinfo=pst)
    
    # Convert to UTC for database comparison (assuming DB stores in UTC)
    yesterday_start_utc = yesterday_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    today_start_utc = today_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    tomorrow_start_utc = tomorrow_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    
    # Get yesterday's results (games that started during yesterday PST)
    yesterday_results = await session.execute(
        select(GameResult)
        .where(
            and_(
                GameResult.start_time >= yesterday_start_utc,
                GameResult.start_time < today_start_utc,
                or_(
                    GameResult.status == "STATUS_FINAL",
                    GameResult.status == "Final",
                    GameResult.status.like("%Final%")
                )
            )
        )
        .order_by(GameResult.start_time)
    )
    results = yesterday_results.scalars().all()
    
    # Get today's upcoming games (games that start during today PST)
    today_upcoming = await session.execute(
        select(GameUpcoming)
        .where(
            and_(
                GameUpcoming.start_time >= today_start_utc,
                GameUpcoming.start_time < tomorrow_start_utc
            )
        )
        .order_by(GameUpcoming.start_time)
    )
    upcoming = today_upcoming.scalars().all()
    
    # Format the output for AI
    output_lines = []
    
    # Yesterday's results
    output_lines.append("=" * 60)
    output_lines.append(f"YESTERDAY'S RESULTS ({yesterday_pst.strftime('%Y-%m-%d')} PST)")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    if results:
        for game in results:
            output_lines.append(f"{game.sport}")
            output_lines.append(f"{game.away_team_name} @ {game.home_team_name}")
            output_lines.append(f"Final Score: {game.away_team_name} {game.away_score} - {game.home_score} {game.home_team_name}")
            if game.game_id:
                output_lines.append(f"Game ID: {game.game_id}")
            output_lines.append("")
    else:
        output_lines.append("No completed games found for yesterday.")
        output_lines.append("")
    
    # Today's upcoming games
    output_lines.append("=" * 60)
    output_lines.append(f"TODAY'S UPCOMING GAMES ({today_pst.strftime('%Y-%m-%d')} PST)")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    if upcoming:
        for game in upcoming:
            output_lines.append(f"{game.sport}")
            output_lines.append(f"{game.away_team_name} @ {game.home_team_name}")
            if game.game_id:
                output_lines.append(f"Game ID: {game.game_id}")
            if game.start_time:
                # Convert UTC time to PST for display
                game_time_pst = game.start_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(pst)
                output_lines.append(f"Start Time: {game_time_pst.strftime('%I:%M %p PST')}")
            if hasattr(game, 'home_odds') and game.home_odds:
                output_lines.append(f"Odds: {game.away_team_name} {game.away_odds} / {game.home_team_name} {game.home_odds}")
            if hasattr(game, 'home_record') and game.home_record:
                output_lines.append(f"Records: {game.away_team_name} ({game.away_record}) / {game.home_team_name} ({game.home_record})")
            output_lines.append("")
    else:
        output_lines.append("No upcoming games found for today.")
        output_lines.append("")
    
    return {
        "text": "\n".join(output_lines),
        "yesterday_count": len(results),
        "today_count": len(upcoming)
    }


@router.get("/{game_id}")
async def game_intel(game_id: str, session: AsyncSession = Depends(get_session)):
    svc = GameIntelligenceService(session)
    return await svc.get_game_intel(game_id)