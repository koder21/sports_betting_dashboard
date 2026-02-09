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


@router.post("/apply-corrections")
async def apply_corrections(
    corrections: List[Dict[str, Any]] = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Apply approved bet corrections after manual verification"""
    verifier = BetVerifier(session)
    return await verifier.apply_corrections(corrections)