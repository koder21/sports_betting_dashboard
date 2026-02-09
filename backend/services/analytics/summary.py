from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from datetime import datetime, timedelta

from .roi import ROIAnalytics, calculate_profit_from_american_odds
from .trends import TrendAnalytics
from .ev_kelly import EVKellyAnalytics
from .trends_detailed import PlayerTrendAnalytics, TeamTrendAnalytics
from .patterns import BettingPatternsAnalytics
from ...repositories.bet_repo import BetRepository


class AnalyticsSummary:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.roi = ROIAnalytics(session)
        self.trends = TrendAnalytics(session)
        self.ev_kelly = EVKellyAnalytics(session)
        self.player_trends = PlayerTrendAnalytics(session)
        self.team_trends = TeamTrendAnalytics(session)
        self.patterns = BettingPatternsAnalytics(session)
        self.bets = BetRepository(session)

    async def full_summary(self) -> Dict[str, Any]:
        roi_data = await self.roi.compute()
        trend_data = await self.trends.win_loss_trend()
        market_data = await self.trends.by_market()
        streak_data = await self.trends.streak_analysis()
        ev_kelly_data = await self.ev_kelly.compute()
        player_trends_data = await self.player_trends.hot_cold_players()
        team_momentum_data = await self.team_trends.team_momentum()
        team_splits_data = await self.team_trends.home_away_splits()
        betting_patterns_data = await self.patterns.compute()
        sport_data = await self.by_sport()
        bet_type_data = await self.by_bet_type()
        time_data = await self.over_time()
        parlay_data = await self.parlay_performance()

        return {
            "roi": roi_data,
            "trends": trend_data,
            "streaks": streak_data,
            "markets": market_data,
            "ev_kelly": ev_kelly_data,
            "player_trends": player_trends_data,
            "team_momentum": team_momentum_data,
            "team_splits": team_splits_data,
            "betting_patterns": betting_patterns_data,
            "by_sport": sport_data,
            "by_bet_type": bet_type_data,
            "over_time": time_data,
            "parlay_performance": parlay_data,
        }

    async def by_sport(self) -> Dict[str, Any]:
        """Analyze performance by sport - COUNT EACH LEG separately"""
        all_bets = await self.bets.list_all_with_relations()
        
        sport_stats = defaultdict(lambda: {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_profit": 0.0
        })
        
        # Count each leg individually
        for bet in all_bets:
            # Try to get sport from game first, then from sport relationship
            sport_name = "Unknown"
            if bet.game and hasattr(bet.game, 'sport') and bet.game.sport:
                sport_name = bet.game.sport
            elif bet.sport and hasattr(bet.sport, 'name') and bet.sport.name:
                sport_name = bet.sport.name
            
            sport_stats[sport_name]["total"] += 1
            sport_stats[sport_name]["total_staked"] += bet.stake or 0
            
            if bet.status == "won":
                sport_stats[sport_name]["won"] += 1
            elif bet.status == "lost":
                sport_stats[sport_name]["lost"] += 1
            elif bet.status == "pending":
                sport_stats[sport_name]["pending"] += 1
            
            if bet.profit is not None:
                sport_stats[sport_name]["total_profit"] += bet.profit
        
        # Calculate win rates and ROI
        for sport, stats in sport_stats.items():
            graded = stats["won"] + stats["lost"]
            stats["win_rate"] = (stats["won"] / graded * 100) if graded > 0 else 0
            # Protect against division by zero and infinity
            if stats["total_staked"] > 0:
                roi_value = (stats["total_profit"] / stats["total_staked"] * 100)
                # Replace inf/nan with 0
                if roi_value != roi_value or roi_value == float('inf') or roi_value == float('-inf'):
                    stats["roi"] = 0.0
                else:
                    stats["roi"] = roi_value
            else:
                stats["roi"] = 0.0
        
        return dict(sport_stats)

    async def by_bet_type(self) -> Dict[str, Any]:
        """Analyze performance by bet type - COUNT EACH LEG separately"""
        all_bets = await self.bets.list_all_with_relations()
        
        type_stats = defaultdict(lambda: {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_profit": 0.0
        })
        
        # Count each leg individually
        for bet in all_bets:
            bet_type = bet.bet_type or "unknown"
            
            type_stats[bet_type]["total"] += 1
            type_stats[bet_type]["total_staked"] += bet.stake or 0
            
            if bet.status == "won":
                type_stats[bet_type]["won"] += 1
            elif bet.status == "lost":
                type_stats[bet_type]["lost"] += 1
            elif bet.status == "pending":
                type_stats[bet_type]["pending"] += 1
            
            if bet.profit is not None:
                type_stats[bet_type]["total_profit"] += bet.profit
        
        # Calculate win rates and ROI
        for bet_type, stats in type_stats.items():
            graded = stats["won"] + stats["lost"]
            stats["win_rate"] = (stats["won"] / graded * 100) if graded > 0 else 0
            # Protect against division by zero and infinity
            if stats["total_staked"] > 0:
                roi_value = (stats["total_profit"] / stats["total_staked"] * 100)
                # Replace inf/nan with 0
                if roi_value != roi_value or roi_value == float('inf') or roi_value == float('-inf'):
                    stats["roi"] = 0.0
                else:
                    stats["roi"] = roi_value
            else:
                stats["roi"] = 0.0
        
        return dict(type_stats)

    async def over_time(self) -> Dict[str, Any]:
        """Analyze performance over time (last 30 days, weekly breakdown)"""
        all_bets = await self.bets.list_all()
        
        # Group by parlay_id first
        parlays_by_id = {}
        for bet in all_bets:
            if bet.parlay_id:
                if bet.parlay_id not in parlays_by_id:
                    parlays_by_id[bet.parlay_id] = []
                parlays_by_id[bet.parlay_id].append(bet)
        
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        
        # Weekly buckets for last 4 weeks
        weekly_stats = []
        for week in range(4):
            week_start = now - timedelta(days=(week + 1) * 7)
            week_end = now - timedelta(days=week * 7)
            
            won = 0
            lost = 0
            total = 0
            profit = 0.0
            
            # Check each bet (parlay) to see if it was placed in this week
            for parlay_id, legs in parlays_by_id.items():
                first_leg = legs[0]
                if first_leg.placed_at and week_start <= first_leg.placed_at < week_end:
                    total += 1
                    
                    # Determine bet status
                    graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
                    pending_legs = [l for l in legs if l.status == "pending"]
                    
                    if not pending_legs:
                        if all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                            won += 1
                            bet_stake = sum(leg.stake or 0 for leg in legs)
                            parlay_odds = legs[0].parlay_odds or 0.0
                            profit += calculate_profit_from_american_odds(bet_stake, parlay_odds)
                        elif any(l.status == "lost" for l in legs):
                            lost += 1
                            bet_stake = sum(leg.stake or 0 for leg in legs)
                            profit -= bet_stake
            
            weekly_stats.append({
                "week": f"Week {4 - week}",
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
                "total": total,
                "won": won,
                "lost": lost,
                "profit": profit,
                "win_rate": (won / (won + lost) * 100) if (won + lost) > 0 else 0
            })
        
        return {
            "weekly": list(reversed(weekly_stats))
        }

    async def parlay_performance(self) -> Dict[str, Any]:
        """Compare parlay performance vs single bets
        
        Singles have 1 leg, parlays have 2+ legs
        - A parlay is WON if all legs are won
        - A parlay is LOST if any leg is lost
        - A parlay is PENDING if not all legs are graded
        """
        all_bets = await self.bets.list_all()
        
        # Group ALL bets by parlay_id first
        bets_by_parlay_id = {}
        for bet in all_bets:
            if bet.parlay_id:
                if bet.parlay_id not in bets_by_parlay_id:
                    bets_by_parlay_id[bet.parlay_id] = []
                bets_by_parlay_id[bet.parlay_id].append(bet)
        
        # Separate singles (1 leg) from parlays (2+ legs)
        single_outcomes = []
        parlay_outcomes = []
        
        for parlay_id, legs in bets_by_parlay_id.items():
            stake = sum(leg.stake or 0 for leg in legs)
            parlay_odds = legs[0].parlay_odds or 0.0
            
            # Determine status
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            if pending_legs:
                status = "pending"
                profit = 0.0
            elif all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                status = "won"
                profit = calculate_profit_from_american_odds(stake, parlay_odds)
            elif any(l.status == "lost" for l in legs):
                status = "lost"
                profit = -stake
            else:
                status = "pending"
                profit = 0.0
            
            outcome = {
                "parlay_id": parlay_id,
                "status": status,
                "legs": len(legs),
                "profit": profit,
                "stake": stake,
                "parlay_odds": parlay_odds
            }
            
            # Separate singles (1 leg) from parlays (2+ legs)
            if len(legs) == 1:
                single_outcomes.append(outcome)
            else:
                parlay_outcomes.append(outcome)
        
        def calc_stats(items):
            if not items:
                return {
                    "total": 0,
                    "won": 0,
                    "lost": 0,
                    "pending": 0,
                    "profit": 0.0,
                    "staked": 0.0,
                    "win_rate": 0.0,
                    "roi": 0.0
                }
            
            won = sum(1 for item in items if item.get("status") == "won")
            lost = sum(1 for item in items if item.get("status") == "lost")
            pending = sum(1 for item in items if item.get("status") == "pending")
            profit = sum(item.get("profit", 0) for item in items)
            staked = sum(item.get("stake", 0) for item in items)
            
            # Calculate ROI with protection against infinity
            if staked > 0:
                roi_value = (profit / staked * 100)
                # Replace inf/nan with 0
                if roi_value != roi_value or roi_value == float('inf') or roi_value == float('-inf'):
                    roi_final = 0.0
                else:
                    roi_final = roi_value
            else:
                roi_final = 0.0
            
            return {
                "total": len(items),
                "won": won,
                "lost": lost,
                "pending": pending,
                "profit": float(profit),
                "staked": float(staked),
                "win_rate": (won / (won + lost) * 100) if (won + lost) > 0 else 0,
                "roi": roi_final
            }
        
        return {
            "singles": calc_stats(single_outcomes),
            "parlays": calc_stats(parlay_outcomes),
            "total_parlays": len(parlay_outcomes),
            "parlay_details": parlay_outcomes
        }