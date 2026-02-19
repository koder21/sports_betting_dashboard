from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from datetime import datetime, timedelta
import math

from .roi import ROIAnalytics, calculate_profit_from_parlay_odds
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

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _group_bets(self, all_bets):
        """Group bets by parlay_id or create single-bet groups (include all bets, even voided)"""
        groups = {}
        for bet in all_bets:
            group_id = bet.parlay_id if bet.parlay_id else f"single-{bet.id}"
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(bet)
        return groups

    def _get_group_status(self, group_bets):
        """Determine the status of a bet group"""
        statuses = [b.status for b in group_bets]
        if any(s == "void" for s in statuses):
            return "void"
        if any(s == "pending" for s in statuses):
            return "pending"
        if all(s == "won" for s in statuses):
            return "won"
        if any(s == "lost" for s in statuses):
            return "lost"
        return "pending"

    def _calculate_group_profit_and_stake(self, group_bets, status):
        """Calculate profit and stake for a bet group (parlay or singles)"""
        is_parlay = len(group_bets) > 1 and group_bets[0].parlay_id
        stake = 0.0
        profit = 0.0

        if is_parlay:
            stake = group_bets[0].original_stake
            if stake is None:
                return 0.0, 0.0
            
            if status == "won":
                parlay_odds = group_bets[0].parlay_odds or 0.0
                # Use decimal odds calculation: profit = stake * (odds - 1)
                profit = stake * (parlay_odds - 1) if parlay_odds >= 1.01 else 0.0
            elif status == "lost":
                profit = -stake
        else:
            # Singles: sum up individual bets
            for b in group_bets:
                s = b.original_stake or b.stake or 0
                stake += s
                if b.status == "won":
                    odds = b.odds or 0.0
                    profit += s * (odds - 1) if odds >= 1.01 else 0.0
                elif b.status == "lost":
                    profit -= s

        # Sanitize values
        if not math.isfinite(profit):
            profit = 0.0
        if not math.isfinite(stake):
            stake = 0.0

        return profit, stake

    def _safe_roi_calculation(self, profit, staked):
        """Calculate ROI with safety checks for infinity/NaN"""
        if staked <= 0:
            return 0.0
        roi_value = (profit / staked * 100)
        return 0.0 if not math.isfinite(roi_value) else roi_value

    def _add_calculated_stats(self, stats):
        """Add win_rate and roi to a stats dictionary"""
        graded = stats["won"] + stats["lost"]
        stats["win_rate"] = (stats["won"] / graded * 100) if graded > 0 else 0
        stats["roi"] = self._safe_roi_calculation(stats["total_profit"], stats["total_staked"])
        return stats

    def _get_sport_name(self, bet_obj):
        """Extract sport name from bet object, normalized to uppercase"""
        # Try direct string field
        sport_name = getattr(bet_obj, 'sport_name', None)
        if sport_name and isinstance(sport_name, str):
            return sport_name.upper()
        # Try related sport object
        sport = getattr(bet_obj, 'sport', None)
        if sport:
            # Try .name or .sport_name on the related object
            name = getattr(sport, 'name', None) or getattr(sport, 'sport_name', None)
            if name and isinstance(name, str):
                return name.upper()
        return "UNKNOWN"

    def _get_source(self, bet_obj):
        """Determine bet source from reason field"""
        source = "Manual"
        if bet_obj.reason:
            reason_lower = bet_obj.reason.lower()
            if "confidence:" in reason_lower or "aai" in reason_lower:
                source = "AAI"
            elif "custom" in reason_lower:
                source = "Custom"
        return source

    # ============================================================================
    # ANALYTICS METHODS
    # ============================================================================

    async def full_summary(self) -> Dict[str, Any]:
        """Generate comprehensive analytics summary"""
        import logging
        logger = logging.getLogger("backend.services.analytics.summary")
        try:
            all_bets = await self.bets.list_all_with_relations(limit=1000000) if self.bets else []
            grouped = self._group_bets(all_bets)

            sport_stats = defaultdict(lambda: {
                "total": 0,
                "won": 0,
                "lost": 0,
                "pending": 0,
                "total_staked": 0.0,
                "total_profit": 0.0
            })
            total_profit = 0.0
            total_staked = 0.0

            logger.info(f"[SUMMARY] Processing {len(grouped)} bet groups for summary")

            for group_id, group_bets in grouped.items():
                sport_name = self._get_sport_name(group_bets[0])
                status = self._get_group_status(group_bets)
                if status == "void":
                    # Still count voided group for voided stat, but skip for profit/stake
                    continue
                profit, stake = self._calculate_group_profit_and_stake(group_bets, status)
                sport_stats[sport_name]["total"] += 1
                sport_stats[sport_name]["total_staked"] += stake
                sport_stats[sport_name]["total_profit"] += profit
                if status == "won":
                    sport_stats[sport_name]["won"] += 1
                elif status == "lost":
                    sport_stats[sport_name]["lost"] += 1
                elif status == "pending":
                    sport_stats[sport_name]["pending"] += 1
                total_profit += profit
                total_staked += stake
                
            # Directly calculate win/loss/voided from grouped bet statuses
            total_bets = len(grouped)
            total_won = 0
            total_lost = 0
            total_pending = 0
            total_voided = 0
            for group_bets in grouped.values():
                status = self._get_group_status(group_bets)
                if status == "won":
                    total_won += 1
                elif status == "lost":
                    total_lost += 1
                elif status == "pending":
                    total_pending += 1
                elif status == "void":
                    total_voided += 1
            win_loss_ratio = (total_won / total_lost) if total_lost > 0 else (float('inf') if total_won > 0 else 0)

            roi_data = await self.roi.compute()
            roi_data["profit"] = total_profit
            roi_data["total_staked"] = total_staked
            roi_data["total_bets"] = total_bets
            roi_data["won"] = total_won
            roi_data["lost"] = total_lost
            roi_data["pending"] = total_pending
            roi_data["voided"] = total_voided
            roi_data["win_loss_ratio"] = win_loss_ratio
            roi_data["win_rate"] = (total_won / (total_won + total_lost) * 100) if (total_won + total_lost) > 0 else 0

            trend_data = await self.trends.win_loss_trend()
            market_data = await self.trends.by_market()
            streak_data = await self.trends.streak_analysis()
            ev_kelly_data = await self.ev_kelly.compute()
            player_trends_data = await self.player_trends.hot_cold_players()
            team_momentum_data = await self.team_trends.team_momentum()
            team_splits_data = await self.team_trends.home_away_splits()

            by_sport = await self.by_sport()
            by_bet_type = await self.by_bet_type()
            over_time = await self.over_time()
            parlay_performance = await self.parlay_performance()
            betting_patterns = await self.patterns.analyze_patterns() if hasattr(self.patterns, 'analyze_patterns') else None
            by_source = await self.by_source()

            return {
                "roi": roi_data,
                "trends": trend_data,
                "streaks": streak_data,
                "markets": market_data,
                "ev_kelly": ev_kelly_data,
                "player_trends": player_trends_data,
                "team_momentum": team_momentum_data,
                "team_splits": team_splits_data,
                "by_sport": by_sport,
                "by_bet_type": by_bet_type,
                "over_time": over_time,
                "parlay_performance": parlay_performance,
                "betting_patterns": betting_patterns,
                "by_source": by_source,
            }
        except Exception as e:
            logger.error("[SUMMARY] Exception in full_summary: %s", e, exc_info=True)
            return {"error": str(e)}

    async def by_sport(self) -> Dict[str, Any]:
        """Analyze performance by sport - each group counted once"""
        all_bets = await self.bets.list_all_with_relations()
        groups = self._group_bets(all_bets)

        sport_stats = defaultdict(lambda: {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_profit": 0.0
        })

        for group_bets in groups.values():
            sport_name = self._get_sport_name(group_bets[0])
            status = self._get_group_status(group_bets)
            
            if status == "void":
                continue

            profit, stake = self._calculate_group_profit_and_stake(group_bets, status)

            sport_stats[sport_name]["total"] += 1
            sport_stats[sport_name]["total_staked"] += stake
            sport_stats[sport_name]["total_profit"] += profit
            
            if status == "won":
                sport_stats[sport_name]["won"] += 1
            elif status == "lost":
                sport_stats[sport_name]["lost"] += 1
            elif status == "pending":
                sport_stats[sport_name]["pending"] += 1

        # Add calculated stats
        for sport, stats in sport_stats.items():
            self._add_calculated_stats(stats)

        return dict(sport_stats)

    async def by_bet_type(self) -> Dict[str, Any]:
        """Analyze performance by bet type - each group counted once"""
        all_bets = await self.bets.list_all_with_relations()
        groups = self._group_bets(all_bets)

        type_stats = defaultdict(lambda: {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_profit": 0.0
        })

        for group_bets in groups.values():
            is_parlay = len(group_bets) > 1 and group_bets[0].parlay_id
            bet_type = "parlay" if is_parlay else (group_bets[0].bet_type or "unknown")
            status = self._get_group_status(group_bets)
            
            if status == "void":
                continue

            profit, stake = self._calculate_group_profit_and_stake(group_bets, status)

            type_stats[bet_type]["total"] += 1
            type_stats[bet_type]["total_staked"] += stake
            type_stats[bet_type]["total_profit"] += profit
            
            if status == "won":
                type_stats[bet_type]["won"] += 1
            elif status == "lost":
                type_stats[bet_type]["lost"] += 1
            elif status == "pending":
                type_stats[bet_type]["pending"] += 1

        # Add calculated stats
        for bet_type, stats in type_stats.items():
            self._add_calculated_stats(stats)

        return dict(type_stats)

    async def over_time(self) -> Dict[str, Any]:
        """Analyze performance over time (last 4 weeks, weekly breakdown)"""
        all_bets = await self.bets.list_all_with_relations()
        
        # Group by parlay_id
        parlays_by_id = {}
        singles = []
        for bet in all_bets:
            if bet.parlay_id:
                if bet.parlay_id not in parlays_by_id:
                    parlays_by_id[bet.parlay_id] = []
                parlays_by_id[bet.parlay_id].append(bet)
            else:
                singles.append(bet)
        
        now = datetime.utcnow()
        weekly_stats = []
        
        for week in range(4):
            week_start = now - timedelta(days=(week + 1) * 7)
            week_end = now - timedelta(days=week * 7)
            
            won = 0
            lost = 0
            total = 0
            profit = 0.0
            
            # Check parlays in this week
            for parlay_id, legs in parlays_by_id.items():
                first_leg = legs[0]
                if first_leg.placed_at and week_start <= first_leg.placed_at < week_end:
                    if any(l.status == "void" for l in legs):
                        continue
                    
                    total += 1
                    status = self._get_group_status(legs)
                    
                    if status != "pending":
                        bet_stake = legs[0].original_stake
                        if bet_stake is None:
                            continue
                        
                        if status == "won":
                            won += 1
                            parlay_odds = legs[0].parlay_odds or 0.0
                            profit += bet_stake * (parlay_odds - 1) if parlay_odds >= 1.01 else 0.0
                        elif status == "lost":
                            lost += 1
                            profit -= bet_stake

            # Check singles in this week
            for bet in singles:
                if bet.status == "void":
                    continue
                if bet.placed_at and week_start <= bet.placed_at < week_end:
                    total += 1
                    if bet.status == "won":
                        won += 1
                        stake = bet.original_stake or bet.stake or 0.0
                        odds = bet.odds or 0.0
                        profit += stake * (odds - 1) if odds >= 1.01 else 0.0
                    elif bet.status == "lost":
                        lost += 1
                        profit -= (bet.original_stake or bet.stake or 0)
            
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
        """Compare parlay performance vs single bets"""
        all_bets = await self.bets.list()
        
        # Group ALL bets by parlay_id
        bets_by_parlay_id = {}
        singles = []
        for bet in all_bets:
            if bet.parlay_id:
                if bet.parlay_id not in bets_by_parlay_id:
                    bets_by_parlay_id[bet.parlay_id] = []
                bets_by_parlay_id[bet.parlay_id].append(bet)
            else:
                singles.append(bet)
        
        single_outcomes = []
        parlay_outcomes = []
        
        # Process parlay groups
        for parlay_id, legs in bets_by_parlay_id.items():
            if any(l.status == "void" for l in legs):
                continue
            
            status = self._get_group_status(legs)
            profit, stake = self._calculate_group_profit_and_stake(legs, status)
            
            outcome = {
                "parlay_id": parlay_id,
                "status": status,
                "legs": len(legs),
                "profit": profit,
                "stake": stake,
                "parlay_odds": legs[0].parlay_odds if len(legs) > 1 else None
            }
            
            # 1-leg parlays are treated as singles
            if len(legs) == 1:
                single_outcomes.append(outcome)
            else:
                parlay_outcomes.append(outcome)
        
        # Add actual singles
        for bet in singles:
            if bet.status == "void":
                continue
            
            stake = bet.original_stake or bet.stake or 0.0
            profit = 0.0
            status = bet.status
            
            if bet.status == "won":
                odds = bet.odds or 0.0
                profit = stake * (odds - 1) if odds >= 1.01 else 0.0
            elif bet.status == "lost":
                profit = -stake

            single_outcomes.append({
                "parlay_id": f"single-{bet.id}",
                "status": status,
                "legs": 1,
                "profit": profit,
                "stake": stake,
                "parlay_odds": None
            })

        # Calculate leg-level wins/losses
        leg_wins = 0
        leg_losses = 0

        for _, legs in bets_by_parlay_id.items():
            if any(l.status == "void" for l in legs):
                continue
            for leg in legs:
                if leg.status == "won":
                    leg_wins += 1
                elif leg.status == "lost":
                    leg_losses += 1

        for bet in singles:
            if bet.status == "void":
                continue
            if bet.status == "won":
                leg_wins += 1
            elif bet.status == "lost":
                leg_losses += 1
        
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
            
            return {
                "total": len(items),
                "won": won,
                "lost": lost,
                "pending": pending,
                "profit": float(profit),
                "staked": float(staked),
                "win_rate": (won / (won + lost) * 100) if (won + lost) > 0 else 0,
                "roi": self._safe_roi_calculation(profit, staked)
            }
        
        return {
            "singles": calc_stats(single_outcomes),
            "parlays": calc_stats(parlay_outcomes),
            "total_parlays": len(parlay_outcomes),
            "parlay_details": parlay_outcomes,
            "leg_wins": leg_wins,
            "leg_losses": leg_losses,
            "leg_total": leg_wins + leg_losses
        }

    async def by_source(self) -> Dict[str, Any]:
        """Analyze performance by bet source (AAI, Custom, Manual)"""
        all_bets = await self.bets.list_all_with_relations()
        
        source_stats = defaultdict(lambda: {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "total_staked": 0.0,
            "total_profit": 0.0
        })
        
        parlays_by_id = defaultdict(list)
        singles = []
        for bet in all_bets:
            if bet.parlay_id:
                parlays_by_id[bet.parlay_id].append(bet)
            else:
                singles.append(bet)
        
        # Separate 1-leg parlays into singles
        one_leg_parlays = [pid for pid, legs in parlays_by_id.items() if len(legs) == 1]
        for pid in one_leg_parlays:
            singles.extend(parlays_by_id[pid])
            del parlays_by_id[pid]

        # Process multi-leg parlays
        for _, legs in parlays_by_id.items():
            if any(l.status == "void" for l in legs):
                continue
            
            source = self._get_source(legs[0])
            status = self._get_group_status(legs)
            profit, stake = self._calculate_group_profit_and_stake(legs, status)

            source_stats[source]["total"] += 1
            source_stats[source]["total_staked"] += stake
            source_stats[source]["total_profit"] += profit
            
            if status == "won":
                source_stats[source]["won"] += 1
            elif status == "lost":
                source_stats[source]["lost"] += 1
            elif status == "pending":
                source_stats[source]["pending"] += 1

        # Process singles
        for bet in singles:
            if bet.status == "void":
                continue
            
            source = self._get_source(bet)
            stake = bet.original_stake or bet.stake or 0
            profit = 0.0
            
            if bet.status == "won":
                odds = bet.odds or 0.0
                profit = stake * (odds - 1) if odds >= 1.01 else 0.0
            elif bet.status == "lost":
                profit = -stake

            source_stats[source]["total"] += 1
            source_stats[source]["total_staked"] += stake
            source_stats[source]["total_profit"] += profit
            
            if bet.status == "won":
                source_stats[source]["won"] += 1
            elif bet.status == "lost":
                source_stats[source]["lost"] += 1
            elif bet.status == "pending":
                source_stats[source]["pending"] += 1
        
        # Add calculated stats
        for source, stats in source_stats.items():
            self._add_calculated_stats(stats)
        
        return dict(source_stats)