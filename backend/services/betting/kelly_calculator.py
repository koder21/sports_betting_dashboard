"""
Kelly Criterion Calculator
===========================
Calculates optimal bet size based on Kelly Criterion formula.

Kelly Formula: f* = (bp - q) / b
Where:
- f* = fraction of bankroll to bet
- b = odds received (decimal - 1)
- p = probability of winning
- q = probability of losing (1-p)

Important: Always use fractional Kelly (1/4 or 1/2) to reduce variance.
"""
from typing import Optional


class KellyCalculator:
    """
    Calculate optimal bet sizing using Kelly Criterion.
    """
    
    # Safety limits
    MAX_KELLY = 0.10  # Never bet more than 10% of bankroll
    MIN_KELLY = 0.001  # Don't bother with <0.1% bets
    
    def calculate_kelly(
        self,
        probability: float,
        decimal_odds: float,
        fractional_kelly: float = 0.25
    ) -> float:
        """
        Calculate Kelly bet size.
        
        Args:
            probability: Win probability (0-1)
            decimal_odds: Decimal odds (e.g., 2.5)
            fractional_kelly: Fraction of full Kelly to use (0-1)
                - 1.0 = Full Kelly (aggressive, high variance)
                - 0.5 = Half Kelly (moderate)
                - 0.25 = Quarter Kelly (conservative, recommended)
        
        Returns:
            Fraction of bankroll to bet (0-1)
        """
        # Validate inputs
        if probability <= 0 or probability >= 1:
            return 0.0
        
        if decimal_odds <= 1.0:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # b = net odds (decimal - 1)
        # p = win probability
        # q = lose probability (1 - p)
        
        b = decimal_odds - 1
        p = probability
        q = 1 - p
        
        # Full Kelly
        kelly = (b * p - q) / b
        
        # Apply fractional Kelly for safety
        kelly_fraction = kelly * fractional_kelly
        
        # Apply safety limits
        kelly_fraction = max(self.MIN_KELLY, min(self.MAX_KELLY, kelly_fraction))
        
        # Don't bet if Kelly is negative (no edge)
        if kelly_fraction < 0:
            return 0.0
        
        return kelly_fraction
    
    def calculate_recommended_stake(
        self,
        bankroll: float,
        probability: float,
        decimal_odds: float,
        fractional_kelly: float = 0.25,
        max_stake: Optional[float] = None
    ) -> dict:
        """
        Calculate recommended stake in dollars.
        
        Args:
            bankroll: Total bankroll ($)
            probability: Win probability (0-1)
            decimal_odds: Decimal odds
            fractional_kelly: Kelly fraction (default 0.25)
            max_stake: Optional max bet limit ($)
        
        Returns:
            Dict with stake recommendations
        """
        # Calculate Kelly fraction
        kelly_frac = self.calculate_kelly(probability, decimal_odds, fractional_kelly)
        
        # Convert to dollar amount
        recommended_stake = bankroll * kelly_frac
        
        # Apply max stake limit if provided
        if max_stake and recommended_stake > max_stake:
            capped_stake = max_stake
            actual_fraction = capped_stake / bankroll
        else:
            capped_stake = recommended_stake
            actual_fraction = kelly_frac
        
        # Calculate expected value
        ev = self._calculate_ev(capped_stake, probability, decimal_odds)
        
        return {
            'kelly_fraction': kelly_frac,
            'recommended_stake': round(recommended_stake, 2),
            'capped_stake': round(capped_stake, 2),
            'actual_fraction': actual_fraction,
            'expected_profit': round(ev, 2),
            'fractional_kelly_used': fractional_kelly,
            'edge_percent': ((decimal_odds * probability) - 1) * 100
        }
    
    def compare_kelly_fractions(
        self,
        bankroll: float,
        probability: float,
        decimal_odds: float
    ) -> dict:
        """
        Compare different Kelly fractions to show variance/return tradeoff.
        
        Returns:
            Dict comparing full Kelly, half Kelly, quarter Kelly
        """
        fractions = {
            'full_kelly': 1.0,
            'half_kelly': 0.5,
            'quarter_kelly': 0.25
        }
        
        results = {}
        
        for name, frac in fractions.items():
            stake_info = self.calculate_recommended_stake(
                bankroll, probability, decimal_odds, frac
            )
            results[name] = stake_info
        
        return results
    
    def _calculate_ev(
        self,
        stake: float,
        probability: float,
        decimal_odds: float
    ) -> float:
        """Calculate expected value of a bet."""
        # EV = (P_win × Profit) - (P_lose × Loss)
        profit_if_win = stake * (decimal_odds - 1)
        loss_if_lose = stake
        
        ev = (probability * profit_if_win) - ((1 - probability) * loss_if_lose)
        return ev
    
    def calculate_kelly_growth_rate(
        self,
        probability: float,
        decimal_odds: float
    ) -> dict:
        """
        Calculate expected growth rate of bankroll using Kelly.
        
        This shows the theoretical long-term growth rate.
        """
        if probability <= 0 or probability >= 1 or decimal_odds <= 1:
            return {"growth_rate": 0}
        
        # Full Kelly growth rate
        b = decimal_odds - 1
        p = probability
        q = 1 - p
        
        # Growth rate formula: g = p*log(1+b*f) + q*log(1-f)
        # where f is Kelly fraction
        kelly_f = (b * p - q) / b
        
        if kelly_f <= 0:
            return {"growth_rate": 0}
        
        # Simplified: growth ≈ f × edge
        edge = (p * b) - q
        growth_rate = kelly_f * edge
        
        return {
            'growth_rate_per_bet': growth_rate,
            'kelly_fraction': kelly_f,
            'edge': edge,
            'interpretation': self._interpret_growth(growth_rate)
        }
    
    def _interpret_growth(self, growth_rate: float) -> str:
        """Interpret what a growth rate means."""
        if growth_rate <= 0:
            return "No edge - do not bet"
        elif growth_rate < 0.02:
            return "Marginal edge - small long-term growth"
        elif growth_rate < 0.05:
            return "Moderate edge - decent long-term growth"
        else:
            return "Strong edge - excellent long-term growth"
    
    def calculate_ruin_probability(
        self,
        bankroll: float,
        edge: float,
        variance: float,
        num_bets: int = 100
    ) -> dict:
        """
        Estimate probability of going broke (ruin).
        
        This is a simplified estimate - actual calculation is complex.
        
        Args:
            bankroll: Starting bankroll
            edge: Expected edge per bet (as fraction, e.g., 0.05 for 5%)
            variance: Variance per bet
            num_bets: Number of bets to simulate
        
        Returns:
            Dict with ruin probability estimate
        """
        if edge <= 0:
            return {"ruin_probability": 1.0, "interpretation": "Negative edge - certain ruin"}
        
        # Simplified Gambler's Ruin formula
        # For positive expectation: P(ruin) ≈ e^(-2 × edge × bankroll / variance)
        
        if variance <= 0:
            variance = 1  # Avoid division by zero
        
        ruin_prob = pow(2.718, (-2 * edge * bankroll / variance))
        
        return {
            'ruin_probability': min(1.0, ruin_prob),
            'interpretation': self._interpret_ruin(ruin_prob),
            'edge': edge,
            'variance': variance
        }
    
    def _interpret_ruin(self, ruin_prob: float) -> str:
        """Interpret ruin probability."""
        if ruin_prob < 0.01:
            return "Very safe - <1% ruin risk"
        elif ruin_prob < 0.05:
            return "Safe - <5% ruin risk"
        elif ruin_prob < 0.10:
            return "Moderate risk - <10% ruin risk"
        elif ruin_prob < 0.25:
            return "High risk - significant ruin chance"
        else:
            return "Very high risk - likely to go broke"