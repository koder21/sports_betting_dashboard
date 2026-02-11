from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.bet_repo import BetRepository
from ...config import settings


def calculate_profit_from_american_odds(stake: float, american_odds: float) -> float:
    """Convert American odds to profit amount.
    
    For positive odds (e.g., +585): profit = stake * (odds / 100)
    For negative odds (e.g., -760): profit = stake / (abs(odds) / 100)
    
    Args:
        stake: The amount wagered
        american_odds: The odds in American format
        
    Returns:
        The profit (positive for wins, negative for losses)
    """
    if american_odds == 0:
        return 0.0
    
    if american_odds > 0:
        # Positive odds: +585 means win $585 on $100 bet
        return stake * (american_odds / 100.0)
    else:
        # Negative odds: -760 means need to bet $760 to win $100
        return stake / (abs(american_odds) / 100.0)


def calculate_profit_from_decimal_odds(stake: float, decimal_odds: float) -> float:
    """Convert decimal odds to profit amount.

    Decimal odds (e.g., 2.50) mean total return = stake * 2.50,
    so profit = stake * (decimal_odds - 1).
    """
    if decimal_odds == 0:
        return 0.0
    return stake * (decimal_odds - 1.0)


def calculate_profit_from_parlay_odds(stake: float, parlay_odds: float) -> float:
    """Handle parlay odds that may be stored as decimal or American.

    Uses a simple heuristic: negative or large magnitude values are treated
    as American odds; otherwise treat as decimal odds.
    """
    if parlay_odds == 0:
        return 0.0
    if parlay_odds <= 0 or abs(parlay_odds) >= 100:
        return calculate_profit_from_american_odds(stake, parlay_odds)
    return calculate_profit_from_decimal_odds(stake, parlay_odds)


class ROIAnalytics:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)

    async def compute(self) -> Dict[str, Any]:
        all_bets = await self.bets.list_all()
        if not all_bets:
            return {"total_bets": 0, "roi": 0.0, "profit": 0.0, "total_legs": 0, "total_staked": 0.0}

        total_staked = 0.0
        total_profit = 0.0
        unique_bets = set()  # Track unique bets (both singles and parlays)

        # Group ALL bets by parlay_id (singles won't have one)
        parlays_by_id = {}
        singles = []
        
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                parlays_by_id[b.parlay_id].append(b)
            else:
                # This is a single bet (no parlay_id)
                singles.append(b)
                unique_bets.add(f"single-{b.id}")
        
        # Separate 1-leg parlays into singles (treat as singles, not parlays)
        one_leg_parlays = [pid for pid, legs in parlays_by_id.items() if len(legs) == 1]
        for pid in one_leg_parlays:
            singles.extend(parlays_by_id[pid])
            del parlays_by_id[pid]
        
        # Track multi-leg parlays
        for pid in parlays_by_id.keys():
            unique_bets.add(pid)

        # Calculate total stake and profit for each parlay
        for parlay_id, legs in parlays_by_id.items():
            if any(l.status == "void" for l in legs):
                continue
            # Use original_stake to get the actual amount staked on the parlay
            # If not available, sum leg stakes
            parlay_stake = legs[0].original_stake if legs[0].original_stake else sum(leg.stake for leg in legs)
            total_staked += parlay_stake
            
            # Check parlay status
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            if pending_legs:
                # Pending parlay - no profit/loss yet
                profit = 0.0
            elif all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                # All legs won - parlay wins with total stake
                parlay_odds = legs[0].parlay_odds or 0.0
                profit = calculate_profit_from_parlay_odds(parlay_stake, parlay_odds)
            elif any(l.status == "lost" for l in legs):
                # Any leg lost - parlay lost, lose total stake
                profit = -parlay_stake
            else:
                # Push or other status
                profit = 0.0
            
            total_profit += profit

        # Calculate total stake and profit for single bets
        for bet in singles:
            if bet.status == "void":
                continue
            stake = bet.original_stake if bet.original_stake else bet.stake
            total_staked += stake
            
            # Calculate profit based on status
            if bet.status == "pending":
                profit = 0.0
            elif bet.status == "won":
                odds = bet.odds or 0.0
                profit = calculate_profit_from_american_odds(stake, odds)
            elif bet.status == "lost":
                profit = -stake
            else:
                # Push, void, or other
                profit = 0.0
            
            total_profit += profit

        # Calculate ROI based on initial bankroll, not total staked
        # ROI = (profit / initial_bankroll) * 100
        bankroll = settings.BANKROLL
        if bankroll > 0:
            roi = (total_profit / bankroll) * 100
            # Replace inf/nan with 0
            if roi != roi or roi == float('inf') or roi == float('-inf'):
                roi = 0.0
        else:
            roi = 0.0

        return {
            "total_bets": len(unique_bets),  # Unique bets (singles + parlays)
            "total_legs": len(all_bets),      # Total legs across all bets
            "total_staked": total_staked,
            "profit": total_profit,
            "roi": roi,
        }