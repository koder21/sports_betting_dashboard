from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from datetime import datetime, timedelta

from ...repositories.bet_repo import BetRepository


class BettingPatternsAnalytics:
    """Analyze betting patterns to identify what works"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)

    async def compute(self) -> Dict[str, Any]:
        """Comprehensive betting patterns analysis"""
        all_bets = await self.bets.list_all_with_relations()
        
        if not all_bets:
            return {
                "best_sports": [],
                "best_bet_types": [],
                "best_days": [],
                "best_hours": [],
                "best_combinations": [],
                "worst_sports": [],
                "worst_bet_types": []
            }
        
        # Filter graded bets only
        graded_bets = [b for b in all_bets if b.status in ["won", "lost"]]
        
        if not graded_bets:
            return {
                "best_sports": [],
                "best_bet_types": [],
                "best_days": [],
                "best_hours": [],
                "best_combinations": [],
                "worst_sports": [],
                "worst_bet_types": []
            }
        
        # Analyze by sport
        sport_stats = defaultdict(lambda: {"won": 0, "lost": 0, "profit": 0.0})
        bet_type_stats = defaultdict(lambda: {"won": 0, "lost": 0, "profit": 0.0})
        day_stats = defaultdict(lambda: {"won": 0, "lost": 0})
        hour_stats = defaultdict(lambda: {"won": 0, "lost": 0})
        combo_stats = defaultdict(lambda: {"won": 0, "lost": 0, "profit": 0.0})
        
        for bet in graded_bets:
            is_win = bet.status == "won"
            sport = bet.sport.name.upper() if bet.sport else "UNKNOWN"
            bet_type = bet.bet_type or "Unknown"
            
            # Sport stats
            sport_stats[sport]["won" if is_win else "lost"] += 1
            if bet.profit:
                sport_stats[sport]["profit"] += float(bet.profit)
            
            # Bet type stats
            bet_type_stats[bet_type]["won" if is_win else "lost"] += 1
            if bet.profit:
                bet_type_stats[bet_type]["profit"] += float(bet.profit)
            
            # Day of week stats
            if bet.placed_at:
                day_name = bet.placed_at.strftime("%A")
                day_stats[day_name]["won" if is_win else "lost"] += 1
            
            # Hour stats
            if bet.placed_at:
                hour = bet.placed_at.hour
                hour_stats[hour]["won" if is_win else "lost"] += 1
            
            # Sport + Bet Type combination
            combo_key = f"{sport} - {bet_type}"
            combo_stats[combo_key]["won" if is_win else "lost"] += 1
            if bet.profit:
                combo_stats[combo_key]["profit"] += float(bet.profit)
        
        # Format results
        best_sports = self._format_stats(sport_stats, min_bets=2)
        best_bet_types = self._format_stats(bet_type_stats, min_bets=2)
        best_combos = self._format_stats(combo_stats, min_bets=1)
        
        # Day of week analysis
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_results = []
        for day in days_order:
            if day in day_stats:
                stats = day_stats[day]
                total = stats["won"] + stats["lost"]
                win_rate = (stats["won"] / total * 100) if total > 0 else 0
                day_results.append({
                    "day": day,
                    "win_rate": round(win_rate, 1),
                    "total": total
                })
        
        # Hour of day analysis
        hour_results = []
        for hour in range(24):
            if hour in hour_stats:
                stats = hour_stats[hour]
                total = stats["won"] + stats["lost"]
                win_rate = (stats["won"] / total * 100) if total > 0 else 0
                hour_results.append({
                    "hour": f"{hour:02d}:00",
                    "hour_num": hour,
                    "win_rate": round(win_rate, 1),
                    "total": total
                })
        
        # Sort for display
        best_sports.sort(key=lambda x: x["win_rate"], reverse=True)
        best_bet_types.sort(key=lambda x: x["win_rate"], reverse=True)
        best_combos.sort(key=lambda x: x["win_rate"], reverse=True)
        worst_sports = sorted(best_sports, key=lambda x: x["win_rate"])[:3]
        worst_bet_types = sorted(best_bet_types, key=lambda x: x["win_rate"])[:3]
        
        return {
            "best_sports": best_sports,
            "best_bet_types": best_bet_types,
            "best_combinations": best_combos[:10],
            "worst_sports": worst_sports,
            "worst_bet_types": worst_bet_types,
            "best_days": sorted(day_results, key=lambda x: x["win_rate"], reverse=True),
            "best_hours": sorted(hour_results, key=lambda x: x["win_rate"], reverse=True)[:5]
        }

    def _format_stats(self, stats_dict: Dict, min_bets: int = 1) -> list:
        """Convert stats dict to formatted list"""
        result = []
        for key, stats in stats_dict.items():
            total = stats["won"] + stats["lost"]
            if total < min_bets:
                continue
            
            win_rate = (stats["won"] / total * 100) if total > 0 else 0
            result.append({
                "name": key,
                "won": stats["won"],
                "lost": stats["lost"],
                "total": total,
                "win_rate": round(win_rate, 1),
                "profit": round(stats["profit"], 2)
            })
        
        return result
