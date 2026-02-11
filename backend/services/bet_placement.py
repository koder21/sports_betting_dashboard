"""
Service to convert AAI recommendations to active pending bets.
Also handles custom bet building from available games.

Uses the same Bet model and storage mechanism as the text-based bet placement system.
All bets are stored identically whether from AAI or manually pasted.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import uuid

from ..models.bet import Bet
from ..models.game import Game
from ..models.sport import Sport


class BetPlacementService:
    """
    Convert AAI picks and custom selections into pending bets.
    
    Ensures all bets are stored with the same structure as manually pasted bets:
    - Same Bet model fields
    - Same status tracking
    - Same parlay grouping mechanism
    - Same odds calculation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def place_aai_single(
        self,
        game_id: str,
        pick: str,  # e.g., "Lakers -5"
        confidence: float,
        combined_confidence: float,
        stake: float,
        odds: float,
        reason: str,
        sport: str
    ) -> Dict[str, Any]:
        """
        Convert an AAI single recommendation into a pending bet.
        
        Stores exactly like a manually pasted single bet.
        
        Returns: Bet details
        """
        try:
            # Get sport ID - case-insensitive lookup
            sport_normalized = sport.upper() if sport else ""
            sport_stmt = select(Sport).where(Sport.name.ilike(sport_normalized))
            sport_result = await self.session.execute(sport_stmt)
            sport_obj = sport_result.scalar_one_or_none()
            
            if not sport_obj:
                raise ValueError(f"Sport '{sport}' not found in database")
            
            # Create bet using same structure as BettingEngine
            bet = Bet(
                placed_at=datetime.utcnow(),  # Use utcnow like engine
                sport_id=sport_obj.id,
                game_id=game_id,
                raw_text=f"AAI Single: {pick}",
                original_stake=stake,  # Track original stake
                stake=stake,  # Actual stake (no division for singles)
                odds=odds,
                bet_type="moneyline",  # Use 'moneyline' like regular single bets, not 'single'
                selection=pick,  # Match engine field names
                reason=f"AAI | Confidence: {combined_confidence}% | {reason}",  # Store confidence in reason
                status="pending",  # Always start as pending
                parlay_id=None  # No parlay for singles
            )
            
            self.session.add(bet)
            await self.session.commit()
            
            # Calculate potential win like the engine does
            potential_win = self._calculate_potential_win(stake, odds)
            
            return {
                "success": True,
                "bet_id": bet.id,
                "game_id": game_id,
                "pick": pick,
                "odds": odds,
                "stake": stake,
                "confidence": combined_confidence,
                "potential_win": potential_win,
                "status": "pending"
            }
        except Exception as e:
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def place_aai_parlay(
        self,
        legs: List[Dict[str, Any]],
        stake: float,
        sport: str
    ) -> Dict[str, Any]:
        """
        Convert multiple AAI picks into a parlay bet.
        
        Stores exactly like a manually pasted parlay (same stakes division, parlay_id grouping).
        """
        try:
            if len(legs) < 2:
                raise ValueError("Parlay requires at least 2 legs")
            
            # Get sport ID
            sport_stmt = select(Sport).where(Sport.name == sport)
            sport_result = await self.session.execute(sport_stmt)
            sport_obj = sport_result.scalar_one_or_none()
            
            if not sport_obj:
                raise ValueError(f"Sport '{sport}' not found")
            
            # Calculate parlay odds (multiply all leg odds)
            parlay_odds = 1.0
            for leg in legs:
                parlay_odds *= leg["odds"]
            
            # Generate parlay ID (same format as BettingEngine)
            parlay_id = str(uuid.uuid4())
            
            # Divide stake equally across legs (same as BettingEngine)
            stake_per_leg = stake / len(legs)
            
            # Build description
            legs_text = " + ".join([leg["pick"] for leg in legs])
            leg_confidences = ", ".join([f"{leg['confidence']}%" for leg in legs])
            
            created_bets = []
            
            # Create one bet record per leg (same as BettingEngine)
            for leg in legs:
                bet = Bet(
                    placed_at=datetime.utcnow(),  # Use utcnow like engine
                    sport_id=sport_obj.id,
                    game_id=leg["game_id"],
                    raw_text=legs_text,
                    original_stake=stake,  # Track original full stake
                    stake=stake_per_leg,  # Divided stake per leg
                    odds=leg["odds"],  # Individual leg odds
                    parlay_id=parlay_id,  # Group all legs by parlay_id
                    bet_type="moneyline",  # Use 'moneyline' so legs get graded (not 'parlay')
                    selection=leg["pick"],
                    reason=f"AAI Parlay | Confidence: {leg['confidence']}% | {leg.get('reason', '')}",
                    status="pending"
                )
                
                self.session.add(bet)
                created_bets.append({
                    "bet_id": None,  # Will be set after commit
                    "game_id": leg["game_id"],
                    "pick": leg["pick"],
                    "odds": leg["odds"]
                })
            
            await self.session.commit()
            
            return {
                "success": True,
                "parlay_id": parlay_id,
                "legs": len(legs),
                "legs_text": legs_text,
                "parlay_odds": parlay_odds,
                "stake": stake,
                "stake_per_leg": stake_per_leg,
                "potential_win": stake * parlay_odds,
                "status": "pending",
                "created_bets": len(created_bets)
            }
        except Exception as e:
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_custom_single(
        self,
        game_id: str,
        pick: str,
        stake: float,
        odds: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Build a custom single bet from available games.
        
        Stores identically to manually placed single bets.
        """
        try:
            # Get game to find sport
            game_stmt = select(Game).where(Game.game_id == game_id)
            game_result = await self.session.execute(game_stmt)
            game_obj = game_result.scalar_one_or_none()
            
            if not game_obj:
                raise ValueError(f"Game {game_id} not found")
            
            # Create custom bet using same structure as BettingEngine
            bet = Bet(
                placed_at=datetime.utcnow(),
                sport_id=game_obj.sport_id,
                game_id=game_id,
                raw_text=f"Custom: {pick}",
                original_stake=stake,
                stake=stake,
                odds=odds,
                bet_type="moneyline",  # Use 'moneyline' like regular single bets
                selection=pick,
                reason=f"Custom Single | {notes}",
                status="pending",
                parlay_id=None
            )
            
            self.session.add(bet)
            await self.session.commit()
            
            potential_win = self._calculate_potential_win(stake, odds)
            
            return {
                "success": True,
                "bet_id": bet.id,
                "game_id": game_id,
                "pick": pick,
                "odds": odds,
                "stake": stake,
                "potential_win": potential_win,
                "status": "pending"
            }
        except Exception as e:
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_custom_parlay(
        self,
        legs: List[Dict[str, Any]],
        stake: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Build a custom parlay from available games.
        
        Stores identically to manually placed parlays (divided stakes, parlay_id grouping).
        
        legs format: [
            {
                "game_id": str,
                "pick": str,
                "odds": float
            },
            ...
        ]
        """
        try:
            if len(legs) < 2:
                raise ValueError("Parlay requires at least 2 legs")
            
            # Verify all games exist and get primary sport
            primary_sport_id = None
            for leg in legs:
                game_stmt = select(Game).where(Game.game_id == leg["game_id"])
                game_result = await self.session.execute(game_stmt)
                game_obj = game_result.scalar_one_or_none()
                
                if not game_obj:
                    raise ValueError(f"Game {leg['game_id']} not found")
                
                if primary_sport_id is None:
                    primary_sport_id = game_obj.sport_id
            
            if not primary_sport_id:
                raise ValueError("Could not determine sport for parlay")
            
            # Calculate odds
            parlay_odds = 1.0
            for leg in legs:
                parlay_odds *= leg["odds"]
            
            # Generate parlay ID (same format as BettingEngine)
            parlay_id = str(uuid.uuid4())
            
            # Divide stake equally (same as BettingEngine)
            stake_per_leg = stake / len(legs)
            
            # Build description
            legs_text = " + ".join([leg["pick"] for leg in legs])
            
            created_bets = []
            
            # Create one bet per leg (same as BettingEngine)
            for leg in legs:
                bet = Bet(
                    placed_at=datetime.utcnow(),
                    sport_id=primary_sport_id,
                    game_id=leg["game_id"],
                    raw_text=legs_text,
                    original_stake=stake,  # Track original full stake
                    stake=stake_per_leg,  # Divided stake per leg
                    odds=leg["odds"],  # Individual leg odds
                    parlay_id=parlay_id,  # Group all legs
                    bet_type="moneyline",  # Use 'moneyline' so legs get graded (not 'parlay')
                    selection=leg["pick"],
                    reason=f"Custom Parlay | {notes}",
                    status="pending"
                )
                
                self.session.add(bet)
                created_bets.append(bet)
            
            await self.session.commit()
            
            return {
                "success": True,
                "parlay_id": parlay_id,
                "legs": len(legs),
                "legs_text": legs_text,
                "parlay_odds": parlay_odds,
                "stake": stake,
                "stake_per_leg": stake_per_leg,
                "potential_win": stake * parlay_odds,
                "status": "pending",
                "created_bets": len(created_bets)
            }
        except Exception as e:
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_potential_win(self, stake: float, odds: float) -> float:
        """
        Calculate potential win for a single bet.
        Uses the same calculation as the BettingEngine.
        """
        return stake * (odds - 1)
