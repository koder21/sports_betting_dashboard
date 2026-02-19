from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.bet_placement import BetPlacementService

router = APIRouter(tags=["bets"])

class PlaceAAISingleRequest(BaseModel):
    game_id: str
    pick: str
    confidence: float
    combined_confidence: float
    stake: float
    odds: float
    reason: str
    sport: str

class ParlayLeg(BaseModel):
    game_id: str
    pick: str
    odds: float
    confidence: Optional[float] = None

class PlaceAAIParlayRequest(BaseModel):
    legs: List[ParlayLeg]
    stake: float
    sport: str

class BuildCustomSingleRequest(BaseModel):
    game_id: str
    pick: str
    stake: float
    odds: float
    notes: Optional[str] = ""

class BuildCustomParlayRequest(BaseModel):
    legs: List[ParlayLeg]
    stake: float
    notes: Optional[str] = ""

@router.post("/place-aai-single")
async def place_aai_single(
    request: PlaceAAISingleRequest,
    session: AsyncSession = Depends(get_db),
):
    service = BetPlacementService(session)
    result = await service.place_aai_single(
        game_id=request.game_id,
        pick=request.pick,
        confidence=request.confidence,
        combined_confidence=request.combined_confidence,
        stake=request.stake,
        odds=request.odds,
        reason=request.reason,
        sport=request.sport,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to place bet"))
    return result

@router.post("/place-aai-parlay")
async def place_aai_parlay(
    request: PlaceAAIParlayRequest,
    session: AsyncSession = Depends(get_db),
):
    service = BetPlacementService(session)
    legs = [
        {
            "game_id": leg.game_id,
            "pick": leg.pick,
            "odds": leg.odds,
            "confidence": leg.confidence or 0.0,
        }
        for leg in request.legs
    ]

    result = await service.place_aai_parlay(legs=legs, stake=request.stake, sport=request.sport)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to place parlay"))
    return result

@router.post("/build-custom-single")
async def build_custom_single(
    request: BuildCustomSingleRequest,
    session: AsyncSession = Depends(get_db),
):
    service = BetPlacementService(session)
    result = await service.build_custom_single(
        game_id=request.game_id,
        pick=request.pick,
        stake=request.stake,
        odds=request.odds,
        notes=request.notes,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to build bet"))
    return result

@router.post("/build-custom-parlay")
async def build_custom_parlay(
    request: BuildCustomParlayRequest,
    session: AsyncSession = Depends(get_db),
):
    service = BetPlacementService(session)
    legs = [
        {
            "game_id": leg.game_id,
            "pick": leg.pick,
            "odds": leg.odds,
            "confidence": leg.confidence if leg.confidence is not None else 0.0,
        }
        for leg in request.legs
    ]

    result = await service.build_custom_parlay(legs=legs, stake=request.stake, notes=request.notes)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to build parlay"))
    return result