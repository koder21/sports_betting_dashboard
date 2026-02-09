from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import math

from ...repositories.bet_repo import BetRepository


def american_to_decimal(american_odds: float) -> float:
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_probability(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability"""
    if decimal_odds <= 0:
        return 0
    return 1 / decimal_odds


def calculate_ev(odds: float, win_probability: float, stake: float) -> float:
    """
    Calculate expected value of a bet
    
    EV = (probability_of_winning * amount_won) - (probability_of_losing * stake)
    
    Args:
        odds: American odds (e.g., -110, +150)
        win_probability: Estimated probability of winning (0-1)
        stake: Bet amount
    
    Returns:
        Expected value in dollars
    """
    decimal_odds = american_to_decimal(odds)
    amount_won = stake * (decimal_odds - 1)
    
    ev = (win_probability * amount_won) - ((1 - win_probability) * stake)
    return ev


def calculate_kelly_fraction(odds: float, win_probability: float, kelly_percentage: float = 1.0) -> float:
    """
    Calculate Kelly Criterion bet sizing
    
    Kelly Formula: f* = (bp - q) / b
    Where:
        f* = fraction of bankroll to bet
        b = decimal odds - 1 (net odds)
        p = probability of winning
        q = probability of losing (1 - p)
    
    Args:
        odds: American odds (e.g., -110, +150)
        win_probability: Estimated probability of winning (0-1)
        kelly_percentage: Apply fractional Kelly (0.25 for quarter Kelly, etc)
    
    Returns:
        Fraction of bankroll to bet (0-1)
    """
    decimal_odds = american_to_decimal(odds)
    b = decimal_odds - 1
    p = win_probability
    q = 1 - p
    
    # Kelly formula
    kelly_fraction = (b * p - q) / b
    
    # Apply kelly percentage (e.g., half-kelly = 0.5)
    kelly_fraction = kelly_fraction * kelly_percentage
    
    # Never bet more than bankroll or go negative
    return max(0, min(kelly_fraction, 1.0))


def is_positive_ev(odds: float, win_probability: float) -> bool:
    """Check if a bet has positive EV"""
    decimal_odds = american_to_decimal(odds)
    implied_probability = decimal_to_probability(decimal_odds)
    return win_probability > implied_probability


class EVKellyAnalytics:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)

    async def compute(self) -> Dict[str, Any]:
        """Compute EV and Kelly metrics for all bets"""
        all_bets = await self.bets.list_all_with_relations()
        
        if not all_bets:
            return {
                "total_ev": 0.0,
                "ev_bets": 0,
                "negative_ev_bets": 0,
                "positive_ev_percentage": 0.0,
                "roi_on_positive_ev": 0.0,
                "roi_on_negative_ev": 0.0,
                "avg_kelly_adherence": 0.0,
                "kelly_analysis": []
            }
        
        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        parlay_odds = {}
        parlay_stakes = {}
        
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                    parlay_odds[b.parlay_id] = []
                    parlay_stakes[b.parlay_id] = b.stake or 0
                parlays_by_id[b.parlay_id].append(b)
                if b.odds:
                    parlay_odds[b.parlay_id].append(float(b.odds))
        
        # Calculate metrics for each parlay
        positive_ev_count = 0
        negative_ev_count = 0
        total_positive_ev = 0.0
        total_negative_ev = 0.0
        positive_ev_roi_values = []
        negative_ev_roi_values = []
        kelly_adherence_values = []
        kelly_analysis_records = []
        
        for parlay_id, legs in parlays_by_id.items():
            stake = parlay_stakes[parlay_id]
            odds_list = parlay_odds[parlay_id]
            
            # Determine parlay outcome
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            if pending_legs:
                continue  # Skip pending bets
            
            # Calculate actual win probability based on parlay result
            is_winner = all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs)
            actual_probability = 1.0 if is_winner else 0.0
            
            if not odds_list:
                continue
            
            # For simplicity, use average odds or first leg
            avg_odds = odds_list[0] if odds_list else -110
            
            # Estimate win probability from historical performance
            # (In real scenario, this would come from your analysis/betting data)
            implied_prob = decimal_to_probability(american_to_decimal(avg_odds))
            estimated_prob = implied_prob + 0.05  # Assume slight edge (5%)
            estimated_prob = min(estimated_prob, 0.99)  # Cap at 99%
            
            # Calculate EV based on actual outcome
            ev = calculate_ev(avg_odds, actual_probability, stake)
            
            # Calculate Kelly-sized bet
            kelly_fraction = calculate_kelly_fraction(avg_odds, estimated_prob, kelly_percentage=0.25)  # Quarter Kelly
            kelly_sized_stake = kelly_fraction * 1000  # Assume $1000 bankroll reference
            
            # Calculate Kelly adherence (how close actual bet was to Kelly)
            if kelly_sized_stake > 0:
                adherence = min(stake / kelly_sized_stake, 1.0) * 100  # Percentage
                kelly_adherence_values.append(adherence)
            
            # Track by EV
            if ev > 0:
                positive_ev_count += 1
                total_positive_ev += ev
                if is_winner:
                    positive_ev_roi_values.append((stake, stake))  # Won
                else:
                    positive_ev_roi_values.append((-stake, stake))  # Lost but was +EV
            else:
                negative_ev_count += 1
                total_negative_ev += ev
                if is_winner:
                    negative_ev_roi_values.append((stake, stake))  # Won but was -EV
                else:
                    negative_ev_roi_values.append((-stake, stake))  # Lost and was -EV
            
            kelly_analysis_records.append({
                "parlay_id": parlay_id,
                "stake": stake,
                "odds": avg_odds,
                "ev": round(ev, 2),
                "is_positive_ev": ev > 0,
                "kelly_fraction": round(kelly_fraction * 100, 1),
                "kelly_sized_stake": round(kelly_sized_stake, 2),
                "actual_stake": stake,
                "kelly_adherence": round(adherence, 1) if kelly_sized_stake > 0 else 0,
                "result": "WON" if is_winner else "LOST"
            })
        
        # Calculate ROI for positive and negative EV bets
        positive_ev_roi = 0.0
        negative_ev_roi = 0.0
        
        if positive_ev_roi_values:
            total_profit = sum(p[0] for p in positive_ev_roi_values)
            total_staked = sum(p[1] for p in positive_ev_roi_values)
            if total_staked > 0:
                positive_ev_roi = (total_profit / total_staked) * 100
        
        if negative_ev_roi_values:
            total_profit = sum(p[0] for p in negative_ev_roi_values)
            total_staked = sum(p[1] for p in negative_ev_roi_values)
            if total_staked > 0:
                negative_ev_roi = (total_profit / total_staked) * 100
        
        total_bets = positive_ev_count + negative_ev_count
        positive_ev_percentage = (positive_ev_count / total_bets * 100) if total_bets > 0 else 0
        avg_kelly_adherence = sum(kelly_adherence_values) / len(kelly_adherence_values) if kelly_adherence_values else 0
        
        return {
            "total_ev": round(total_positive_ev + total_negative_ev, 2),
            "ev_bets": positive_ev_count,
            "negative_ev_bets": negative_ev_count,
            "positive_ev_percentage": round(positive_ev_percentage, 1),
            "roi_on_positive_ev": round(positive_ev_roi, 2),
            "roi_on_negative_ev": round(negative_ev_roi, 2),
            "avg_kelly_adherence": round(avg_kelly_adherence, 1),
            "kelly_analysis": kelly_analysis_records[-20:]  # Last 20 bets
        }
