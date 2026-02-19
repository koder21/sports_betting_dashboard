import logging
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.analytics.summary import AnalyticsSummary
from ..services.analytics.trends_detailed import TeamTrendAnalytics

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/summary")
async def analytics_summary(session: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    try:
        svc = AnalyticsSummary(session)
        return await svc.full_summary()
    except Exception as exc:
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"[SUMMARY ENDPOINT] Exception: {exc}\nTraceback:\n{tb_str}")
        return {"error": str(exc), "traceback": tb_str}


@router.get("/team-momentum")
async def get_team_momentum(
    team_ids: Optional[List[str]] = Query(None),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get momentum status for teams (FIRE: 4+ wins in last 5, FREEZING: 4+ losses in last 5).
    """
    tracker = TeamTrendAnalytics(session)
    momentum_data = await tracker.team_momentum(games_window=5)
    
    teams = momentum_data.get("momentum", [])
    
    if team_ids:
        teams = [t for t in teams if t["team_id"] in team_ids]
    
    return {team["team_id"]: team for team in teams}