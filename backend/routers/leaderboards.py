"""Analytics endpoints for forecaster leaderboards and consensus analysis."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..db import get_session
from ..repositories.forecaster_leaderboard import ForecasterLeaderboardRepo
from ..services.weather import WeatherService

router = APIRouter()


@router.get("/forecasters/leaderboard")
async def get_forecaster_leaderboard(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    days: int = Query(90, description="Days of history to include"),
    limit: int = Query(50, description="Max results"),
    session: AsyncSession = Depends(get_session),
):
    """Get forecaster/model performance leaderboard ranked by ROI."""
    repo = ForecasterLeaderboardRepo(session)
    leaderboard = await repo.get_leaderboard(sport=sport, days=days, limit=limit)
    return {
        "status": "ok",
        "period": f"Last {days} days",
        "count": len(leaderboard),
        "leaderboard": leaderboard
    }


@router.get("/forecasters/{forecaster}/stats")
async def get_forecaster_stats(
    forecaster: str,
    days: int = Query(90, description="Days of history"),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed stats for a specific forecaster."""
    repo = ForecasterLeaderboardRepo(session)
    stats = await repo.get_forecaster_stats(forecaster, days=days)
    return {
        "status": "ok",
        "stats": stats
    }


@router.get("/forecasters/{forecaster}/by-sport")
async def get_forecaster_accuracy_by_sport(
    forecaster: str,
    days: int = Query(90, description="Days of history"),
    session: AsyncSession = Depends(get_session),
):
    """Get forecaster accuracy breakdown by sport."""
    repo = ForecasterLeaderboardRepo(session)
    breakdown = await repo.get_accuracy_by_sport(forecaster, days=days)
    return {
        "status": "ok",
        "forecaster": forecaster,
        "breakdown": breakdown
    }


@router.get("/forecasters/{forecaster}/streak")
async def get_forecaster_streak(
    forecaster: str,
    session: AsyncSession = Depends(get_session),
):
    """Get current win/loss streak for a forecaster."""
    repo = ForecasterLeaderboardRepo(session)
    streak = await repo.get_win_streak(forecaster)
    return {
        "status": "ok",
        "forecaster": forecaster,
        "streak": streak
    }


@router.get("/forecasters/{forecaster}/contrarian")
async def get_forecaster_contrarian_picks(
    forecaster: str,
    days: int = Query(30, description="Days of history"),
    min_roi: float = Query(10.0, description="Minimum ROI threshold"),
    session: AsyncSession = Depends(get_session),
):
    """Get forecaster's best contrarian/high-ROI picks."""
    repo = ForecasterLeaderboardRepo(session)
    picks = await repo.get_contrarian_picks(forecaster, days=days, min_roi=min_roi)
    return {
        "status": "ok",
        "forecaster": forecaster,
        "min_roi": min_roi,
        "picks": picks
    }


@router.get("/weather/{venue}")
async def get_weather_for_venue(
    venue: str,
    city: Optional[str] = Query(None, description="City name"),
    sport: Optional[str] = Query(None, description="Sport for impact analysis"),
):
    """Get weather for a venue and impact on sports betting."""
    service = WeatherService()
    
    if sport:
        impact = await service.get_weather_impact_on_game(venue, sport, city)
        return {
            "status": "ok",
            "venue": venue,
            "city": city,
            "sport": sport,
            **impact
        }
    else:
        weather = await service.get_weather_for_venue(venue, city)
        return {
            "status": "ok" if weather else "error",
            "venue": venue,
            "city": city,
            "weather": {
                "temp": weather.temp,
                "wind_speed": weather.wind_speed,
                "wind_direction": weather.wind_direction,
                "humidity": weather.humidity,
                "precipitation": weather.precipitation,
                "condition": weather.condition,
                "feels_like": weather.feels_like,
                "is_harsh": weather.is_harsh()
            } if weather else None
        }
