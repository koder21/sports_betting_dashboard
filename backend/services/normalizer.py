from typing import Dict, Any


class StatNormalizer:
    @staticmethod
    def normalize_boxscore(raw: Dict[str, Any]) -> Dict[str, float]:
        out = {
            "points": 0.0,
            "rebounds": 0.0,
            "assists": 0.0,
            "yards_pass": 0.0,
            "yards_rush": 0.0,
            "yards_rec": 0.0,
            "td_pass": 0.0,
            "td_rush": 0.0,
            "td_rec": 0.0,
            "shots": 0.0,
            "saves": 0.0,
            "goals": 0.0,
            "sig_strikes": 0.0,
            "takedowns": 0.0,
        }

        if not raw:
            return out

        mapping = {
            "points": ["points", "pts"],
            "rebounds": ["reb", "rebounds"],
            "assists": ["ast", "assists"],
            "yards_pass": ["passingYards"],
            "yards_rush": ["rushingYards"],
            "yards_rec": ["receivingYards"],
            "td_pass": ["passingTouchdowns"],
            "td_rush": ["rushingTouchdowns"],
            "td_rec": ["receivingTouchdowns"],
            "shots": ["shotsOnGoal", "shots"],
            "saves": ["saves"],
            "goals": ["goals"],
            "sig_strikes": ["sigStrikes"],
            "takedowns": ["takedowns"],
        }

        for key, aliases in mapping.items():
            for alias in aliases:
                if alias in raw:
                    out[key] = float(raw.get(alias, 0.0))
                    break

        return out