from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from ..db import get_session
from ..services.betting.engine import BettingEngine
from ..services.betting.verifier import BetVerifier

router = APIRouter()


@router.post("/place")
async def place_bet(
    raw_text: str,
    stake: float,
    odds: float,
    session: AsyncSession = Depends(get_session),
):
    engine = BettingEngine(session)
    return await engine.place_bet(raw_text, stake, odds)


@router.post("/place-multiple")
async def place_bets_from_text(
    raw_text: str,
    session: AsyncSession = Depends(get_session),
):
    engine = BettingEngine(session)
    return await engine.place_bets_from_text(raw_text)


@router.get("/all")
async def get_all_bets(session: AsyncSession = Depends(get_session)):
    engine = BettingEngine(session)
    bets = await engine.get_bets_with_details()
    return {"status": "ok", "bets": bets}


@router.post("/grade")
async def grade_bets(session: AsyncSession = Depends(get_session)):
    engine = BettingEngine(session)
    return await engine.grade_all_pending()


@router.post("/verify")
async def verify_bets(session: AsyncSession = Depends(get_session)):
    """Re-check all graded bets against actual game data"""
    verifier = BetVerifier(session)
    return await verifier.verify_all_graded_bets()


@router.delete("/pending/{bet_id}")
async def delete_pending_bet(bet_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a single pending bet"""
    from sqlalchemy import delete, select
    from ..models.bet import Bet
    
    # Get the bet first to verify it exists and is pending
    result = await session.execute(select(Bet).where(Bet.id == bet_id))
    bet = result.scalar_one_or_none()
    
    if not bet:
        return {"status": "error", "message": f"Bet {bet_id} not found"}
    
    if bet.status != "pending":
        return {"status": "error", "message": f"Only pending bets can be deleted. This bet is {bet.status}"}
    
    # Delete the bet
    await session.execute(delete(Bet).where(Bet.id == bet_id))
    await session.commit()
    
    return {"status": "ok", "message": f"Deleted pending bet {bet_id}"}


@router.delete("/pending-all")
async def delete_all_pending_bets(session: AsyncSession = Depends(get_session)):
    """Delete all pending bets"""
    from sqlalchemy import delete, select
    from ..models.bet import Bet
    
    # Count pending bets first
    result = await session.execute(select(Bet).where(Bet.status == "pending"))
    pending_bets = result.scalars().all()
    count = len(pending_bets)
    
    if count == 0:
        return {"status": "ok", "message": "No pending bets to delete", "deleted": 0}
    
    # Delete all pending bets
    await session.execute(delete(Bet).where(Bet.status == "pending"))
    await session.commit()
    
    return {"status": "ok", "message": f"Deleted {count} pending bets", "deleted": count}


@router.post("/apply-corrections")
async def apply_corrections(
    corrections: List[Dict[str, Any]] = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Apply approved bet corrections after manual verification"""
    verifier = BetVerifier(session)
    return await verifier.apply_corrections(corrections)