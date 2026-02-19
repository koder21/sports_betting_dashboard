from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.betting.engine import BettingEngine

router = APIRouter(tags=["bets"])

@router.get("/pending")
async def get_pending_bets(session: AsyncSession = Depends(get_db)):
    """
    Return all pending bets.
    """
    engine = BettingEngine(session)
    return await engine.bets.list_pending()