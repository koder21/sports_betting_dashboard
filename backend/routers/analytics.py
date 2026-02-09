from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.analytics.summary import AnalyticsSummary

router = APIRouter()


@router.get("/summary")
async def analytics_summary(session: AsyncSession = Depends(get_session)):
    svc = AnalyticsSummary(session)
    return await svc.full_summary()