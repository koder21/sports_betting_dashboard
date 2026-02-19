
from fastapi import APIRouter, Depends, Body, HTTPException, Request
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from ..db import get_db
from ..services.betting.engine import BettingEngine
from ..services.betting.verifier import BetVerifier

router = APIRouter()

# Apply corrections endpoint for /api/bets/apply-corrections
@router.post("/apply-corrections", status_code=status.HTTP_200_OK)
async def apply_corrections(request: Request, session: AsyncSession = Depends(get_db)):
    """
    Apply approved corrections to bets and parlays.
    """
    data = await request.json()
    corrections = data if isinstance(data, list) else data.get("corrections", [])
    verifier = BetVerifier(session)
    try:
        result = await verifier.apply_corrections(corrections)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_bets(session: AsyncSession = Depends(get_db)):
    """
    Verify all bets for discrepancies. Returns verification results.
    """
    verifier = BetVerifier(session)
    try:
        results = await verifier.verify_all_graded_bets()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Restore get all bets endpoint in correct place
@router.get("/all")
async def get_all_bets(session: AsyncSession = Depends(get_db)):
    engine = BettingEngine(session)
    bets = await engine.get_bets_with_details()
    return {"status": "ok", "bets": bets}

# Delete all bets in a parlay group by parlay_id
@router.delete("/parlay/{parlay_id}")
async def delete_parlay(parlay_id: str, session: AsyncSession = Depends(get_db)):
    """Delete all bets in a parlay group by parlay_id"""
    from sqlalchemy import delete, select
    from ..models.bet import Bet

    # Find all bets with this parlay_id
    result = await session.execute(select(Bet).where(Bet.parlay_id == parlay_id))
    bets = result.scalars().all()
    if not bets:
        raise HTTPException(status_code=404, detail=f"No bets found for parlay_id {parlay_id}")

    # Only allow delete if all bets are deletable (won/lost/finished/pending)
    allowed_statuses = {"won", "lost", "finished", "pending"}
    for bet in bets:
        if bet.status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Bet {bet.id} in parlay has status '{bet.status}' and cannot be deleted.")

    await session.execute(delete(Bet).where(Bet.parlay_id == parlay_id))
    await session.commit()
    return {"status": "ok", "message": f"Deleted parlay {parlay_id} ({len(bets)} bets)"}

@router.delete("/finished/{bet_id}")
async def delete_finished_bet(bet_id: int, session: AsyncSession = Depends(get_db)):
    """Delete a single finished, won, or lost bet"""
    from sqlalchemy import delete, select
    from ..models.bet import Bet

    # Get the bet first to verify it exists and is finished/won/lost
    result = await session.execute(select(Bet).where(Bet.id == bet_id))
    bet = result.scalar_one_or_none()

    if not bet:
        return {"status": "error", "message": f"Bet {bet_id} not found"}

    if bet.status not in ("finished", "won", "lost"):
        return {"status": "error", "message": f"Only finished, won, or lost bets can be deleted. This bet is {bet.status}"}

    # Delete the bet
    await session.execute(delete(Bet).where(Bet.id == bet_id))
    await session.commit()

    return {"status": "ok", "message": f"Deleted bet {bet_id}"}


@router.delete("/finished-all")
async def delete_all_finished_bets(session: AsyncSession = Depends(get_db)):
    """Delete all finished, won, or lost bets"""
    from sqlalchemy import delete, select, or_
    from ..models.bet import Bet

    # Count all completed bets
    result = await session.execute(
        select(Bet).where(
            or_(Bet.status == "finished", Bet.status == "won", Bet.status == "lost")
        )
    )
    completed_bets = result.scalars().all()
    count = len(completed_bets)

    if count == 0:
        return {"status": "ok", "message": "No finished/won/lost bets to delete", "deleted": 0}

    # Delete all completed bets
    await session.execute(
        delete(Bet).where(
            or_(Bet.status == "finished", Bet.status == "won", Bet.status == "lost")
        )
    )
    await session.commit()

    return {"status": "ok", "message": f"Deleted {count} finished/won/lost bets", "deleted": count}