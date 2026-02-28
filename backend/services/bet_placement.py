from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import re
from ..models.bet import Bet
from ..models.game import Game
from ..models.sport import Sport


class BetPlacementService:
    """Convert AAI picks and custom selections into pending bets."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ============================================================================
    # HELPER METHODS (extracted common logic)
    # ============================================================================
    
    async def _get_sport(self, sport_name: str) -> Sport:
        """Get sport object by name (case-insensitive)."""
        stmt = select(Sport).where(Sport.name.ilike(sport_name.lower()))
        result = await self.session.execute(stmt)
        sport_obj = result.scalar_one_or_none()
        
        if not sport_obj:
            raise ValueError(f"Sport '{sport_name}' not found in database")
        
        return sport_obj
    

    async def _get_game(self, game_id: str) -> Game:
        """Get game object by ID. Checks both games and games_upcoming tables."""
        from ..models.games_upcoming import GameUpcoming
        stmt = select(Game).where(Game.game_id == game_id)
        result = await self.session.execute(stmt)
        game_obj = result.scalar_one_or_none()
        if not game_obj:
            # Try games_upcoming
            stmt2 = select(GameUpcoming).where(GameUpcoming.game_id == game_id)
            result2 = await self.session.execute(stmt2)
            game_obj = result2.scalar_one_or_none()
            if not game_obj:
                raise ValueError(f"Game {game_id} not found")
        return game_obj
    
    def _calculate_potential_win(self, stake: float, odds: float) -> float:
        """Calculate potential win using decimal odds."""
        return stake * (odds - 1)
    
    def _calculate_parlay_odds(self, leg_odds: List[float]) -> float:
        """Calculate combined parlay odds from individual leg odds."""
        parlay_odds = 1.0
        for odds in leg_odds:
            # Normalize to decimal if needed
            if odds >= 1.01 and odds < 20:
                parlay_odds *= odds
            elif odds > 0:  # American positive
                parlay_odds *= (odds / 100) + 1
            else:  # American negative
                parlay_odds *= (100 / abs(odds)) + 1
        return round(parlay_odds, 4)
    
    async def _create_single_bet(
        self,
        game_id: str,
        pick: str,
        stake: float,
        odds: float,
        reason: str,
        sport_id: int
    ) -> Bet:
        """Create a single bet record."""
        bet = Bet(
            placed_at=datetime.utcnow(),
            sport_id=sport_id,
            game_id=game_id,
            raw_text=f"Single: {pick}",
            original_stake=stake,
            stake=stake,
            odds=odds,
            bet_type="moneyline",
            selection=pick,
            reason=reason,
            status="pending",
            parlay_id=None
        )
        self.session.add(bet)
        return bet
    
    async def _create_parlay_legs(
        self,
        legs: List[Dict[str, Any]],
        stake: float,
        parlay_id: str,
        sport_id: int,
        reason_prefix: str
    ) -> List[Bet]:
        """Create parlay leg bet records."""
        stake_per_leg = stake / len(legs)
        legs_text = " + ".join([leg["pick"] for leg in legs])
        
        created_bets = []
        for leg in legs:
            pick = leg["pick"]
            pick_lower = pick.lower()
            team_total_pattern = re.match(r"^[a-zA-Z\s]+/[a-zA-Z\s]+\s+(over|under)\s+\d+", pick)
            player_prop_pattern = re.match(r"^[a-zA-Z\s\.'-]+\s+(over|under)\s+\d+", pick)

            if " ml" in pick_lower or "moneyline" in pick_lower:
                bet_type = "moneyline"
            elif team_total_pattern:
                bet_type = "total"
            elif player_prop_pattern:
                bet_type = "prop"
            elif "over" in pick_lower or "under" in pick_lower:
                bet_type = "total"
            else:
                bet_type = "moneyline"

            bet = Bet(
                placed_at=datetime.utcnow(),
                sport_id=sport_id,
                game_id=leg["game_id"],
                raw_text=legs_text,
                original_stake=stake,
                stake=stake_per_leg,
                odds=leg["odds"],
                parlay_id=parlay_id,
                bet_type=bet_type,
                selection=pick,
                reason=f"{reason_prefix} | {leg.get('confidence', '')}% | {leg.get('reason', '')}".strip(),
                status="pending"
            )
            self.session.add(bet)
            created_bets.append(bet)
        
        return created_bets
    
    # ============================================================================
    # PUBLIC API METHODS
    # ============================================================================
    
    async def place_aai_single(
        self,
        game_id: str,
        pick: str,
        confidence: float,
        combined_confidence: float,
        stake: float,
        odds: float,
        reason: str,
        sport: str
    ) -> Dict[str, Any]:
        """Convert an AAI single recommendation into a pending bet."""
        try:
            sport_obj = await self._get_sport(sport)
            
            bet = await self._create_single_bet(
                game_id=game_id,
                pick=pick,
                stake=stake,
                odds=odds,
                reason=f"AAI | Confidence: {combined_confidence}% | {reason}",
                sport_id=sport_obj.id
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "bet_id": bet.id,
                "game_id": game_id,
                "pick": pick,
                "odds": odds,
                "stake": stake,
                "confidence": combined_confidence,
                "potential_win": self._calculate_potential_win(stake, odds),
                "status": "pending"
            }
        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}
    
    async def place_aai_parlay(
        self,
        legs: List[Dict[str, Any]],
        stake: float,
        sport: str
    ) -> Dict[str, Any]:
        """Convert multiple AAI picks into a parlay bet."""
        try:
            if len(legs) < 2:
                raise ValueError("Parlay requires at least 2 legs")
            
            sport_obj = await self._get_sport(sport)
            
            # Calculate parlay odds
            parlay_odds = self._calculate_parlay_odds([leg["odds"] for leg in legs])
            
            # Generate parlay ID
            parlay_id = str(uuid.uuid4())
            
            # Create leg bets
            created_bets = await self._create_parlay_legs(
                legs=legs,
                stake=stake,
                parlay_id=parlay_id,
                sport_id=sport_obj.id,
                reason_prefix="AAI Parlay | Confidence"
            )
            
            await self.session.commit()
            
            legs_text = " + ".join([leg["pick"] for leg in legs])
            
            return {
                "success": True,
                "parlay_id": parlay_id,
                "legs": len(legs),
                "legs_text": legs_text,
                "parlay_odds": parlay_odds,
                "stake": stake,
                "stake_per_leg": stake / len(legs),
                "potential_win": stake * parlay_odds,
                "status": "pending",
                "created_bets": len(created_bets)
            }
        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}
    
    async def build_custom_single(
        self,
        game_id: str,
        pick: str,
        stake: float,
        odds: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Build a custom single bet from available games."""
        try:
            game_obj = await self._get_game(game_id)
            
            bet = await self._create_single_bet(
                game_id=game_id,
                pick=pick,
                stake=stake,
                odds=odds,
                reason=f"Custom Single | {notes}",
                sport_id=game_obj.sport_id
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "bet_id": bet.id,
                "game_id": game_id,
                "pick": pick,
                "odds": odds,
                "stake": stake,
                "potential_win": self._calculate_potential_win(stake, odds),
                "status": "pending"
            }
        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}
    
    async def build_custom_parlay(
        self,
        legs: List[Dict[str, Any]],
        stake: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Build a custom parlay from available games.
        
        legs format: [{"game_id": str, "pick": str, "odds": float}, ...]
        """
        try:
            if len(legs) < 2:
                raise ValueError("Parlay requires at least 2 legs")
            
            # Verify all games exist and get primary sport
            primary_sport_id = None
            for leg in legs:
                game_obj = await self._get_game(leg["game_id"])
                if primary_sport_id is None:
                    primary_sport_id = game_obj.sport_id
            
            if not primary_sport_id:
                raise ValueError("Could not determine sport for parlay")
            
            # Calculate odds
            parlay_odds = self._calculate_parlay_odds([leg["odds"] for leg in legs])
            
            # Generate parlay ID
            parlay_id = str(uuid.uuid4())
            
            # Create leg bets
            created_bets = await self._create_parlay_legs(
                legs=legs,
                stake=stake,
                parlay_id=parlay_id,
                sport_id=primary_sport_id,
                reason_prefix=f"Custom Parlay | {notes}"
            )
            
            await self.session.commit()
            
            legs_text = " + ".join([leg["pick"] for leg in legs])
            
            return {
                "success": True,
                "parlay_id": parlay_id,
                "legs": len(legs),
                "legs_text": legs_text,
                "parlay_odds": parlay_odds,
                "stake": stake,
                "stake_per_leg": stake / len(legs),
                "potential_win": stake * parlay_odds,
                "status": "pending",
                "created_bets": len(created_bets)
            }
        except Exception as e:
            await self.session.rollback()
            return {"success": False, "error": str(e)}