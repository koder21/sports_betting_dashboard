from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..db import get_session
from ..services.analytics.summary import AnalyticsSummary
from ..services.analytics.trends_detailed import TeamTrendAnalytics

router = APIRouter()


@router.get("/summary")
async def analytics_summary(session: AsyncSession = Depends(get_session)):
    svc = AnalyticsSummary(session)
    return await svc.full_summary()


@router.get("/team-momentum")
async def get_team_momentum(
    team_ids: Optional[List[str]] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Get momentum status for teams (FIRE: 4+ wins in last 5, FREEZING: 4+ losses in last 5).
    If team_ids provided, filter to those teams only.
    """
    tracker = TeamTrendAnalytics(session)
    momentum_data = await tracker.team_momentum(games_window=5)
    
    teams = momentum_data.get("momentum", [])
    
    # Filter by team_ids if provided
    if team_ids:
        teams = [t for t in teams if t["team_id"] in team_ids]
    
    # Convert to a dict keyed by team_id for easy lookup
    return {team["team_id"]: team for team in teams}