from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi import status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List

from ..db import get_db
from ..models.bet import Bet
from ..services.betting.engine import BettingEngine
from ..services.betting.verifier import BetVerifier

router = APIRouter()


# ── Place bets ────────────────────────────────────────────────────────────────

class PlaceFromTextRequest(BaseModel):
    raw_text: str


@router.post("/place-from-text")
async def place_bets_from_text(
    request: PlaceFromTextRequest,
    session: AsyncSession = Depends(get_db),
):
    """Parse and place all bets from raw pasted text in one atomic transaction."""
    engine = BettingEngine(session)
    result = await engine.place_bets_from_text(request.raw_text)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/all")
async def get_all_bets(session: AsyncSession = Depends(get_db)):
    engine = BettingEngine(session)
    bets = await engine.get_bets_with_details()
    return {"status": "ok", "bets": bets}


# ── Verify / corrections ──────────────────────────────────────────────────────

@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_bets(session: AsyncSession = Depends(get_db)):
    """Verify all graded bets for discrepancies."""
    verifier = BetVerifier(session)
    try:
        return await verifier.verify_all_graded_bets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-corrections", status_code=status.HTTP_200_OK)
async def apply_corrections(request: Request, session: AsyncSession = Depends(get_db)):
    """Apply approved corrections to bets and parlays."""
    data = await request.json()
    corrections = data if isinstance(data, list) else data.get("corrections", [])
    verifier = BetVerifier(session)
    try:
        return await verifier.apply_corrections(corrections)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Delete: parlays ───────────────────────────────────────────────────────────

@router.delete("/parlay/{parlay_id}")
async def delete_parlay(parlay_id: str, session: AsyncSession = Depends(get_db)):
    """Delete all legs of a parlay by parlay_id."""
    result = await session.execute(select(Bet).where(Bet.parlay_id == parlay_id))
    bets = result.scalars().all()

    if not bets:
        raise HTTPException(status_code=404, detail=f"No bets found for parlay_id {parlay_id}")

    allowed_statuses = {"won", "lost", "finished", "pending"}
    for bet in bets:
        if bet.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Bet {bet.id} has status '{bet.status}' and cannot be deleted",
            )

    await session.execute(delete(Bet).where(Bet.parlay_id == parlay_id))
    await session.commit()
    return {"status": "ok", "message": f"Deleted parlay {parlay_id} ({len(bets)} bets)"}


# ── Delete: finished ──────────────────────────────────────────────────────────

@router.delete("/finished/{bet_id}")
async def delete_finished_bet(bet_id: int, session: AsyncSession = Depends(get_db)):
    """Delete a single finished, won, or lost bet."""
    result = await session.execute(select(Bet).where(Bet.id == bet_id))
    bet = result.scalar_one_or_none()

    if not bet:
        raise HTTPException(status_code=404, detail=f"Bet {bet_id} not found")
    if bet.status not in ("finished", "won", "lost"):
        raise HTTPException(
            status_code=400,
            detail=f"Only finished/won/lost bets can be deleted here. Bet {bet_id} is '{bet.status}'",
        )

    await session.execute(delete(Bet).where(Bet.id == bet_id))
    await session.commit()
    return {"status": "ok", "message": f"Deleted bet {bet_id}"}


@router.delete("/finished-all")
async def delete_all_finished_bets(session: AsyncSession = Depends(get_db)):
    """Delete all finished, won, or lost bets."""
    result = await session.execute(
        select(Bet).where(or_(Bet.status == "finished", Bet.status == "won", Bet.status == "lost"))
    )
    bets = result.scalars().all()
    count = len(bets)

    if count == 0:
        return {"status": "ok", "message": "No finished/won/lost bets to delete", "deleted": 0}

    await session.execute(
        delete(Bet).where(or_(Bet.status == "finished", Bet.status == "won", Bet.status == "lost"))
    )
    await session.commit()
    return {"status": "ok", "message": f"Deleted {count} finished/won/lost bets", "deleted": count}


# ── Delete: pending ───────────────────────────────────────────────────────────
# NOTE: These were previously in bets_pending.py which was not mounted.
# Consolidated here so no app.include_router change is needed.

@router.get("/pending")
async def get_pending_bets(session: AsyncSession = Depends(get_db)):
    """Return all pending bets."""
    engine = BettingEngine(session)
    return await engine.bets.list_pending()


@router.delete("/pending-all")
async def delete_all_pending_bets(session: AsyncSession = Depends(get_db)):
    """Delete all pending bets."""
    result = await session.execute(select(Bet).where(Bet.status == "pending"))
    count = len(result.scalars().all())

    if count == 0:
        return {"status": "ok", "message": "No pending bets to delete", "deleted": 0}

    await session.execute(delete(Bet).where(Bet.status == "pending"))
    await session.commit()
    return {"status": "ok", "message": f"Deleted {count} pending bets", "deleted": count}


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