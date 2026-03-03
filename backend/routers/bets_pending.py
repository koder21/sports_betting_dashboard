from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.bet import Bet
from ..services.betting.engine import BettingEngine

router = APIRouter(tags=["bets"])


@router.get("/pending")
async def get_pending_bets(session: AsyncSession = Depends(get_db)):
    """Return all pending bets."""
    engine = BettingEngine(session)
    return await engine.bets.list_pending()


@router.delete("/pending/{bet_id}")
async def delete_pending_bet(bet_id: int, session: AsyncSession = Depends(get_db)):
    """Delete a single pending bet by ID."""
    result = await session.execute(select(Bet).where(Bet.id == bet_id))
    bet = result.scalar_one_or_none()

    if not bet:
        raise HTTPException(status_code=404, detail=f"Bet {bet_id} not found")
    if bet.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending bets can be deleted this way. Bet {bet_id} is '{bet.status}'",
        )

    await session.execute(delete(Bet).where(Bet.id == bet_id))
    await session.commit()
    return {"status": "ok", "message": f"Deleted pending bet {bet_id}"}


@router.delete("/pending-all")
async def delete_all_pending_bets(session: AsyncSession = Depends(get_db)):
    """Delete all pending bets."""
    result = await session.execute(select(Bet).where(Bet.status == "pending"))
    pending_bets = result.scalars().all()
    count = len(pending_bets)

    if count == 0:
        return {"status": "ok", "message": "No pending bets to delete", "deleted": 0}

    await session.execute(delete(Bet).where(Bet.status == "pending"))
    await session.commit()
    return {"status": "ok", "message": f"Deleted {count} pending bets", "deleted": count}