"""
Statistical Models Aggregator
==============================
Combines multiple betting models:
- Elo ratings
- Pythagorean expectation
- Recent form (weighted)
- Home advantage
- Vegas consensus
"""
from typing import Any, Dict, List, Optional
import math

from sqlalchemy.ext.asyncio import AsyncSession


class ModelsAggregator:
    """
    Aggregates win probabilities from multiple statistical models.
    """
    
    # Model weights (can be tuned based on historical accuracy)
    WEIGHTS = {
        'elo': 0.30,
        'pythagorean': 0.25,
        'recent_form': 0.20,
        'home_advantage': 0.10,
        'vegas': 0.15
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_win_probability(
        self,
        game_data: Dict[str, Any],
        team_name: str,
        is_home: bool,
        context: Dict[str, Any],
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated win probability from all models.
        
        Returns:
            Dict with:
            - consensus: Weighted average probability
            - confidence: Model agreement score (0-100)
            - breakdown: Individual model probabilities
        """
        probabilities = {}
        
        # Get probabilities from each model
        elo_prob = await self._elo_model(game_data, team_name, is_home, context)
        if elo_prob is not None:
            probabilities['elo'] = elo_prob
        
        pyth_prob = await self._pythagorean_model(game_data, team_name, is_home, context)
        if pyth_prob is not None:
            probabilities['pythagorean'] = pyth_prob
        
        form_prob = await self._recent_form_model(game_data, team_name, is_home, context)
        if form_prob is not None:
            probabilities['recent_form'] = form_prob
        
        home_prob = self._home_advantage_model(is_home, game_data.get('sport'))
        if home_prob is not None:
            probabilities['home_advantage'] = home_prob
        
        vegas_prob = self._vegas_model(game_data, is_home)
        if vegas_prob is not None:
            probabilities['vegas'] = vegas_prob
        
        # Calculate weighted consensus
        weighted_sum = 0
        total_weight = 0
        
        for model, prob in probabilities.items():
            weight = self.WEIGHTS.get(model, 0.1)
            weighted_sum += prob * weight
            total_weight += weight
        
        consensus = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Calculate model agreement (confidence)
        confidence = self._calculate_confidence(probabilities, consensus)
        
        return {
            'consensus': consensus,
            'confidence': confidence,
            'breakdown': probabilities,
            'models_used': list(probabilities.keys())
        }
    
    async def _elo_model(
        self,
        game_data: Dict[str, Any],
        team_name: str,
        is_home: bool,
        context: Dict[str, Any]
    ) -> Optional[float]:
        """
        Elo rating model.
        
        Estimates team strength from recent win/loss record.
        """
        home_form = context.get('home_form')
        away_form = context.get('away_form')
        
        if not home_form or not away_form:
            return None
        
        # Convert win rates to Elo ratings
        # Base rating: 1500
        # Each 0.1 win rate difference ≈ 60 Elo points
        home_elo = 1500 + (home_form['win_rate'] - 0.5) * 600
        away_elo = 1500 + (away_form['win_rate'] - 0.5) * 600
        
        # Add home advantage (~30 Elo points)
        home_elo += 30
        
        # Calculate win probability using Elo formula
        if is_home:
            elo_diff = home_elo - away_elo
        else:
            elo_diff = away_elo - home_elo
        
        probability = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # Clamp to reasonable range
        return max(0.05, min(0.95, probability))
    
    async def _pythagorean_model(
        self,
        game_data: Dict[str, Any],
        team_name: str,
        is_home: bool,
        context: Dict[str, Any]
    ) -> Optional[float]:
        """
        Pythagorean expectation model.
        
        Uses points scored/allowed to estimate true win probability.
        Formula: win% = (points_for^exp) / (points_for^exp + points_against^exp)
        """
        team_form = context.get('home_form' if is_home else 'away_form')
        opp_form = context.get('away_form' if is_home else 'home_form')
        
        if not team_form or not opp_form:
            return None
        
        if team_form['games_played'] == 0:
            return None
        
        # Get average points for/against
        team_ppg = team_form.get('avg_points_for', 0)
        team_papg = team_form.get('avg_points_against', 0)
        
        if team_ppg <= 0 or team_papg <= 0:
            return None
        
        # Pythagorean exponent varies by sport
        sport = game_data.get('sport', 'NBA')
        if sport in ['NBA', 'NCAAB']:
            exponent = 13.91  # Basketball
        elif sport in ['NFL', 'NCAAF']:
            exponent = 2.37   # Football
        elif sport == 'MLB':
            exponent = 1.83   # Baseball
        elif sport == 'NHL':
            exponent = 2.0    # Hockey
        else:
            exponent = 2.0    # Default
        
        # Calculate Pythagorean expectation
        pyth_win_pct = (team_ppg ** exponent) / (
            (team_ppg ** exponent) + (team_papg ** exponent)
        )
        
        # Adjust for opponent strength
        opp_ppg = opp_form.get('avg_points_for', team_ppg)
        opp_papg = opp_form.get('avg_points_against', team_papg)
        
        if opp_ppg > 0 and opp_papg > 0:
            opp_pyth = (opp_ppg ** exponent) / (
                (opp_ppg ** exponent) + (opp_papg ** exponent)
            )
            
            # Combine team and opponent expectations
            # This gives a matchup-specific probability
            combined = (pyth_win_pct + (1 - opp_pyth)) / 2
            return max(0.05, min(0.95, combined))
        
        return max(0.05, min(0.95, pyth_win_pct))
    
    async def _recent_form_model(
        self,
        game_data: Dict[str, Any],
        team_name: str,
        is_home: bool,
        context: Dict[str, Any]
    ) -> Optional[float]:
        """
        Recent form model with exponential weighting.
        
        Recent games weighted more heavily than older games.
        """
        team_form = context.get('home_form' if is_home else 'away_form')
        opp_form = context.get('away_form' if is_home else 'home_form')
        
        if not team_form or not opp_form:
            return None
        
        # Simple model: use win rate but adjust for opponent
        team_wr = team_form.get('win_rate', 0.5)
        opp_wr = opp_form.get('win_rate', 0.5)
        
        # Relative strength
        if team_wr + opp_wr == 0:
            return 0.5
        
        probability = team_wr / (team_wr + opp_wr)
        
        # Add small home advantage if applicable
        if is_home:
            probability += 0.03
        
        return max(0.05, min(0.95, probability))
    
    def _home_advantage_model(
        self,
        is_home: bool,
        sport: Optional[str] = None
    ) -> float:
        """
        Home field/court advantage model.
        
        Historical home win rates by sport:
        - NBA: 58%
        - NFL: 57%
        - NHL: 55%
        - MLB: 54%
        - College: 60%+ (stronger home advantage)
        """
        if not is_home:
            return 0.46  # Away disadvantage
        
        # Home advantage varies by sport
        if sport in ['NBA']:
            return 0.58
        elif sport in ['NFL']:
            return 0.57
        elif sport in ['NHL']:
            return 0.55
        elif sport in ['MLB']:
            return 0.54
        elif sport in ['NCAAB', 'NCAAF']:
            return 0.60  # College has stronger home advantage
        else:
            return 0.55  # Default
    
    def _vegas_model(
        self,
        game_data: Dict[str, Any],
        is_home: bool
    ) -> Optional[float]:
        """
        Vegas implied probability from moneyline odds.
        
        Vegas is historically very accurate, so this is valuable signal.
        """
        odds = game_data.get('odds_home' if is_home else 'odds_away')
        
        if not odds:
            return None
        
        # Convert American odds to implied probability
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)
        
        # Remove vig (assume ~5% vig split between both sides)
        # This gives us a fairer probability
        devigged_prob = implied_prob * 0.975
        
        return max(0.05, min(0.95, devigged_prob))
    
    def _calculate_confidence(
        self,
        probabilities: Dict[str, float],
        consensus: float
    ) -> float:
        """
        Calculate confidence score based on model agreement.
        
        High agreement = high confidence
        Disagreement = low confidence (indicates uncertainty)
        
        Returns: 0-100 confidence score
        """
        if len(probabilities) < 2:
            return 50  # Default for single model
        
        # Calculate standard deviation of probabilities
        values = list(probabilities.values())
        mean = sum(values) / len(values)
        
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # Low std dev = high confidence
        # 0 std dev → 100 confidence
        # 0.2 std dev → 0 confidence
        confidence = max(0, 100 * (1 - (std_dev * 5)))
        
        # Bonus confidence if consensus is far from 50/50
        edge_bonus = abs(consensus - 0.5) * 50
        
        # Combine
        total_confidence = (confidence * 0.7) + (edge_bonus * 0.3)
        
        return min(100, max(0, total_confidence))
