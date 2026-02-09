from typing import Dict, Any, List
from statistics import mean


class UsageModel:
    @staticmethod
    def compute_usage(stats: List[Dict[str, float]]) -> float:
        if not stats:
            return 0.0
        values = [s.get("points", 0) + s.get("rebounds", 0) + s.get("assists", 0) for s in stats]
        return mean(values)


class MatchupModel:
    @staticmethod
    def compute_matchup_factor(team_stats: List[Dict[str, float]]) -> float:
        if not team_stats:
            return 1.0
        defense = mean([s.get("points", 0) for s in team_stats])
        return max(0.5, min(1.5, 100 / (defense + 1)))


class ProjectionModel:
    @staticmethod
    def project(value: float, usage: float, matchup: float) -> float:
        return value * (0.8 + usage * 0.01) * matchup