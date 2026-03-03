"""
Betting Recommendations System
===============================

Provides data-driven betting recommendations using:
- Statistical models (Elo, Pythagorean expectation)
- Kelly Criterion for optimal bet sizing
- Expected value calculation
- Value betting detection
- Risk-adjusted confidence scoring

Example Usage:
-------------
from services.betting import RecommendationsEngine

async def get_bets(session, bankroll=1000):
    engine = RecommendationsEngine(session, bankroll=bankroll)
    
    recommendations = await engine.get_todays_recommendations(
        min_confidence=60,
        sports=['NBA', 'NFL']
    )
    
    return recommendations
"""

from .recommendations_engine import RecommendationsEngine, BettingRecommendation
from .models_aggregator import ModelsAggregator
from .value_calculator import ValueCalculator
from .kelly_calculator import KellyCalculator

__version__ = '2.0.0'

__all__ = [
    'RecommendationsEngine',
    'BettingRecommendation',
    'ModelsAggregator',
    'ValueCalculator',
    'KellyCalculator',
]