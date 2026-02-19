from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.bet import Bet
from ..models.sport import Sport


class ForecasterLeaderboardRepo:
    """
    Analytical repository for forecaster performance metrics.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_roi_expr(self, profit_col, stake_col):
        """Reusable SQL expression for ROI."""
        return (profit_col / func.nullif(stake_col, 0)) * 100

    def _get_win_rate_expr(self, wins_col, total_col):
        """Reusable SQL expression for Win Rate."""
        return (wins_col / func.nullif(total_col, 0)) * 100

    async def get_leaderboard(
        self,
        sport: Optional[int] = None,
        days: int = 90,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        total_bets = func.count(Bet.id)
        total_wagered = func.coalesce(func.sum(Bet.stake), 0)
        total_profit = func.coalesce(func.sum(Bet.profit), 0)
        wins = func.count(Bet.id).filter(Bet.profit > 0)

        roi_expr = self._get_roi_expr(total_profit, total_wagered).label("roi")
        win_rate_expr = self._get_win_rate_expr(wins, total_bets).label("win_rate")

        query = (
            select(
                Bet.reason.label("forecaster"),
                total_bets.label("total_bets"),
                total_wagered.label("total_wagered"),
                total_profit.label("total_profit"),
                wins.label("wins"),
                roi_expr,
                win_rate_expr,
            )
            .where(
                and_(
                    Bet.status == "graded",
                    Bet.graded_at >= cutoff_date,
                    Bet.reason.is_not(None),
                )
            )
            .group_by(Bet.reason)
            .order_by(desc("roi"))
            .limit(limit)
        )

        if sport is not None:
            query = query.where(Bet.sport_id == sport)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "forecaster": row.forecaster or "unknown",
                "total_bets": int(row.total_bets),
                "total_wagered": float(row.total_wagered),
                "total_profit": float(row.total_profit),
                "wins": int(row.wins),
                "roi": round(float(row.roi or 0), 2),
                "win_rate": round(float(row.win_rate or 0), 2),
                "avg_odds": round(float(row.total_wagered / row.total_bets), 2)
                if row.total_bets
                else 0.0,
            }
            for row in rows
        ]

    async def get_forecaster_stats(
        self,
        forecaster: str,
        days: int = 90,
    ) -> Dict[str, Any]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                func.count(Bet.id).label("total_bets"),
                func.coalesce(func.sum(Bet.stake), 0).label("total_wagered"),
                func.coalesce(func.sum(Bet.profit), 0).label("total_profit"),
                func.count(Bet.id).filter(Bet.profit > 0).label("wins"),
                func.count(Bet.id).filter(Bet.profit < 0).label("losses"),
                func.coalesce(func.avg(Bet.profit), 0).label("avg_profit"),
                func.coalesce(func.max(Bet.profit), 0).label("biggest_win"),
                func.coalesce(func.min(Bet.profit), 0).label("biggest_loss"),
            )
            .where(
                and_(
                    Bet.status == "graded",
                    Bet.graded_at >= cutoff_date,
                    Bet.reason == forecaster,
                )
            )
        )

        result = await self.session.execute(query)
        row = result.first()

        if not row or row.total_bets == 0:
            return {"error": "No data found"}

        roi = (row.total_profit / row.total_wagered * 100) if row.total_wagered else 0.0
        win_rate = (row.wins / row.total_bets * 100) if row.total_bets else 0.0

        return {
            "forecaster": forecaster,
            "period_days": days,
            "total_bets": int(row.total_bets),
            "total_wagered": float(row.total_wagered),
            "total_profit": float(row.total_profit),
            "roi": round(float(roi), 2),
            "wins": int(row.wins),
            "losses": int(row.losses),
            "win_rate": round(float(win_rate), 2),
            "avg_profit_per_bet": round(float(row.avg_profit), 2),
            "biggest_win": float(row.biggest_win),
            "biggest_loss": float(row.biggest_loss),
        }

    async def get_accuracy_by_sport(
        self,
        forecaster: str,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        total_bets = func.count(Bet.id)
        total_profit = func.coalesce(func.sum(Bet.profit), 0)
        total_wagered = func.coalesce(func.sum(Bet.stake), 0)
        wins = func.count(Bet.id).filter(Bet.profit > 0)

        roi_expr = self._get_roi_expr(total_profit, total_wagered).label("roi")
        win_rate_expr = self._get_win_rate_expr(wins, total_bets).label("win_rate")

        query = (
            select(
                Sport.name,
                total_bets.label("total_bets"),
                total_profit.label("total_profit"),
                roi_expr,
                win_rate_expr,
            )
            .join(Sport, Bet.sport_id == Sport.id)
            .where(
                and_(
                    Bet.status == "graded",
                    Bet.graded_at >= cutoff_date,
                    Bet.reason == forecaster,
                )
            )
            .group_by(Sport.name)
            .order_by(desc("roi"))
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "sport": row.name,
                "bets": int(row.total_bets),
                "roi": round(float(row.roi or 0), 2),
                "win_rate": round(float(row.win_rate or 0), 2),
                "profit": float(row.total_profit),
            }
            for row in rows
        ]

    async def get_win_streak(self, forecaster: str) -> Dict[str, Any]:
        """
        Calculates current streak (wins or losses) based on last 20 bets.
        """
        query = (
            select(Bet.profit, Bet.graded_at)
            .where(
                and_(
                    Bet.status == "graded",
                    Bet.reason == forecaster,
                )
            )
            .order_by(desc(Bet.graded_at))
            .limit(20)
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        if not rows:
            return {"current_streak": 0, "streak_type": "none"}

        streak = 0
        first_profit = rows[0].profit
        streak_type = "wins" if first_profit > 0 else "losses"

        for row in rows:
            profit = row.profit
            is_win = profit > 0
            if (streak_type == "wins" and is_win) or (streak_type == "losses" and not is_win):
                streak += 1
            else:
                break

        return {
            "current_streak": streak,
            "streak_type": streak_type,
            "recent_bets": [
                {
                    "profit": float(row.profit),
                    "graded_at": str(row.graded_at),
                }
                for row in rows
            ],
        }

    async def get_contrarian_picks(
        self,
        forecaster: str,
        days: int = 30,
        min_roi: float = 10.0,
    ) -> List[Dict[str, Any]]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        roi_col = ((Bet.profit / func.nullif(Bet.stake, 0)) * 100).label("roi")

        query = (
            select(
                Bet.raw_text,
                Bet.stake,
                Bet.profit,
                Bet.odds,
                Bet.placed_at,
                Bet.graded_at,
                roi_col,
            )
            .where(
                and_(
                    Bet.status == "graded",
                    Bet.graded_at >= cutoff_date,
                    Bet.reason == forecaster,
                    Bet.profit > 0,
                )
            )
            .order_by(desc("roi"))
            .limit(20)
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "bet": row.raw_text,
                "stake": float(row.stake),
                "profit": float(row.profit),
                "roi": round(float(row.roi or 0), 2),
                "odds": float(row.odds),
                "placed_at": str(row.placed_at),
                "graded_at": str(row.graded_at),
            }
            for row in rows
            if (row.roi or 0) >= min_roi
        ]