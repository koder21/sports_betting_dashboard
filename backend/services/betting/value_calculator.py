"""
Value Calculator
================
Detects positive expected value (EV) betting opportunities.

Key Concepts:
- EV = (Probability × Profit) - ((1-Probability) × Loss)
- Positive EV = Long-term profit opportunity
- Edge = How much better your probability is vs market
"""
from typing import Dict, Any


class ValueCalculator:
    """
    Calculate betting value and expected value.
    """
    
    # Minimum edges for different confidence levels
    MIN_EDGE_HIGH_CONF = 2.0  # 2% edge for 70%+ confidence
    MIN_EDGE_MED_CONF = 3.0   # 3% edge for 55-70% confidence
    MIN_EDGE_LOW_CONF = 5.0   # 5% edge for <55% confidence
    
    def calculate_value(
        self,
        model_probability: float,
        market_probability: float,
        model_confidence: float = 50
    ) -> Dict[str, Any]:
        """
        Calculate betting value.
        
        Args:
            model_probability: Your estimated win probability (0-1)
            market_probability: Market's implied probability (0-1)
            model_confidence: Confidence in your model (0-100)
        
        Returns:
            Dict with:
            - edge_percent: Your edge over the market (%)
            - ev_percent: Expected value as % of stake
            - has_value: Boolean if this is a value bet
            - value_rating: Quality rating (excellent/good/marginal/none)
        """
        # Calculate edge (difference between your prob and market prob)
        edge = model_probability - market_probability
        edge_percent = edge * 100
        
        # Calculate expected value
        # EV = (P_win × Profit) - (P_lose × Loss)
        # For decimal odds: Profit = (1/market_prob - 1) × stake
        if market_probability > 0:
            decimal_odds = 1 / market_probability
            profit_multiplier = decimal_odds - 1
            
            ev = (model_probability * profit_multiplier) - ((1 - model_probability) * 1)
            ev_percent = ev * 100
        else:
            ev_percent = 0
        
        # Determine if this has value based on confidence
        has_value = self._has_sufficient_edge(edge_percent, model_confidence)
        
        # Rate the value
        value_rating = self._rate_value(edge_percent, ev_percent, model_confidence)
        
        return {
            'edge_percent': edge_percent,
            'ev_percent': ev_percent,
            'has_value': has_value,
            'value_rating': value_rating,
            'model_probability': model_probability,
            'market_probability': market_probability,
            'implied_odds': 1 / model_probability if model_probability > 0 else 0
        }
    
    def _has_sufficient_edge(self, edge_percent: float, confidence: float) -> bool:
        """
        Determine if edge is sufficient given confidence level.
        
        Higher confidence = lower edge required
        Lower confidence = higher edge required (to compensate for uncertainty)
        """
        if confidence >= 70:
            return edge_percent >= self.MIN_EDGE_HIGH_CONF
        elif confidence >= 55:
            return edge_percent >= self.MIN_EDGE_MED_CONF
        else:
            return edge_percent >= self.MIN_EDGE_LOW_CONF
    
    def _rate_value(
        self,
        edge_percent: float,
        ev_percent: float,
        confidence: float
    ) -> str:
        """
        Rate the quality of the value bet.
        
        Returns: "excellent", "good", "marginal", or "none"
        """
        if edge_percent < 2.0:
            return "none"
        
        # Combine edge and confidence for rating
        value_score = edge_percent * (confidence / 100)
        
        if value_score >= 5.0 and ev_percent >= 10:
            return "excellent"
        elif value_score >= 3.0 and ev_percent >= 5:
            return "good"
        elif value_score >= 2.0 and ev_percent >= 2:
            return "marginal"
        else:
            return "none"
    
    def calculate_closing_line_value(
        self,
        opening_odds: float,
        closing_odds: float,
        bet_odds: float
    ) -> Dict[str, Any]:
        """
        Calculate Closing Line Value (CLV).
        
        CLV is a key metric - beating the closing line is highly correlated
        with long-term profitability.
        
        Args:
            opening_odds: Opening line (decimal)
            closing_odds: Closing line (decimal)
            bet_odds: Odds you got (decimal)
        
        Returns:
            Dict with CLV analysis
        """
        # Did you beat the closing line?
        beat_closing = bet_odds > closing_odds
        
        # How much better?
        clv_percent = ((bet_odds - closing_odds) / closing_odds) * 100
        
        # Line movement
        line_moved = closing_odds - opening_odds
        line_moved_percent = (line_moved / opening_odds) * 100
        
        return {
            'beat_closing_line': beat_closing,
            'clv_percent': clv_percent,
            'line_movement': line_moved,
            'line_movement_percent': line_moved_percent,
            'bet_odds': bet_odds,
            'closing_odds': closing_odds,
            'opening_odds': opening_odds
        }
    
    def detect_steam_move(
        self,
        line_history: list,
        threshold_percent: float = 3.0
    ) -> Dict[str, Any]:
        """
        Detect steam moves (sharp money moving the line quickly).
        
        Steam moves indicate sharp bettors are betting one side heavily.
        
        Args:
            line_history: List of (timestamp, odds) tuples
            threshold_percent: % move to qualify as steam (default 3%)
        
        Returns:
            Dict with steam detection results
        """
        if len(line_history) < 2:
            return {"has_steam": False}
        
        # Get most recent move
        latest_odds = line_history[-1][1]
        previous_odds = line_history[-2][1]
        
        # Calculate movement
        move_percent = abs((latest_odds - previous_odds) / previous_odds) * 100
        
        is_steam = move_percent >= threshold_percent
        
        # Direction
        if latest_odds > previous_odds:
            direction = "up"  # Underdog gaining value
        else:
            direction = "down"  # Favorite strengthening
        
        return {
            'has_steam': is_steam,
            'move_percent': move_percent,
            'direction': direction,
            'latest_odds': latest_odds,
            'previous_odds': previous_odds,
            'interpretation': self._interpret_steam(is_steam, direction)
        }
    
    def _interpret_steam(self, has_steam: bool, direction: str) -> str:
        """Interpret what a steam move means."""
        if not has_steam:
            return "No significant line movement"
        
        if direction == "down":
            return "Sharp money on favorite - line strengthening"
        else:
            return "Sharp money on underdog - line weakening"
