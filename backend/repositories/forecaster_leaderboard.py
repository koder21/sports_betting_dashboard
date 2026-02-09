"""Repository for forecaster/model performance leaderboards."""
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from ..models.bet import Bet


class ForecasterLeaderboardRepo:
    """Track and rank forecaster performance."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_leaderboard(self, 
                             sport: Optional[str] = None,
                             days: int = 90,
                             limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get forecaster leaderboard ranked by ROI.
        
        Args:
            sport: Filter by sport (None = all)
            days: Days of history to consider
            limit: Max results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Query graded bets only
        query = select(
            Bet.reason,
            func.count(Bet.id).label("total_bets"),
            func.sum(Bet.stake).label("total_wagered"),
            func.sum(Bet.profit).label("total_profit"),
            func.count(Bet.id).filter(Bet.profit > 0).label("wins"),
        ).where(
            and_(
                Bet.status == "graded",
                Bet.graded_at >= cutoff_date,
                Bet.reason.isnot(None)
            )
        )
        
        if sport:
            query = query.where(
                Bet.sport_id == (
                    select(func.id).from_(
                        select(func.id).select_from(
                            select().select_from(Bet).where(
                                Bet.sport_id == sport
                            )
                        )
                    )
                )
            )
        
        query = query.group_by(Bet.reason)
        
        results = await self.session.execute(query)
        rows = results.fetchall()
        
        leaderboard = []
        for row in rows:
            reason, total_bets, total_wagered, total_profit, wins = row
            
            if not total_wagered or total_wagered == 0:
                continue
            
            roi = (total_profit / total_wagered) * 100 if total_wagered else 0
            win_rate = (wins / total_bets * 100) if total_bets else 0
            
            leaderboard.append({
                "forecaster": reason or "unknown",
                "total_bets": int(total_bets),
                "total_wagered": float(total_wagered),
                "total_profit": float(total_profit),
                "wins": int(wins),
                "roi": round(roi, 2),
                "win_rate": round(win_rate, 2),
                "avg_odds": round(total_wagered / total_bets, 2) if total_bets else 0
            })
        
        # Sort by ROI descending
        leaderboard.sort(key=lambda x: x["roi"], reverse=True)
        
        return leaderboard[:limit]
    
    async def get_forecaster_stats(self, forecaster: str, days: int = 90) -> Dict[str, Any]:
        """Get detailed stats for a single forecaster."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            func.count(Bet.id).label("total_bets"),
            func.sum(Bet.stake).label("total_wagered"),
            func.sum(Bet.profit).label("total_profit"),
            func.count(Bet.id).filter(Bet.profit > 0).label("wins"),
            func.count(Bet.id).filter(Bet.profit < 0).label("losses"),
            func.avg(Bet.profit).label("avg_profit_per_bet"),
            func.max(Bet.profit).label("biggest_win"),
            func.min(Bet.profit).label("biggest_loss"),
        ).where(
            and_(
                Bet.status == "graded",
                Bet.graded_at >= cutoff_date,
                Bet.reason == forecaster
            )
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return {"error": "No data found"}
        
        total_bets, total_wagered, total_profit, wins, losses, avg_profit, biggest_win, biggest_loss = row
        
        roi = (total_profit / total_wagered * 100) if total_wagered and total_wagered > 0 else 0
        win_rate = (wins / total_bets * 100) if total_bets else 0
        
        return {
            "forecaster": forecaster,
            "period_days": days,
            "total_bets": int(total_bets),
            "total_wagered": float(total_wagered or 0),
            "total_profit": float(total_profit or 0),
            "roi": round(roi, 2),
            "wins": int(wins or 0),
            "losses": int(losses or 0),
            "win_rate": round(win_rate, 2),
            "avg_profit_per_bet": round(float(avg_profit or 0), 2),
            "biggest_win": float(biggest_win or 0),
            "biggest_loss": float(biggest_loss or 0),
        }
    
    async def get_accuracy_by_sport(self, 
                                   forecaster: str,
                                   days: int = 90) -> List[Dict[str, Any]]:
        """Get forecaster accuracy breakdown by sport."""
        from ..models.sport import Sport
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            Sport.name,
            func.count(Bet.id).label("total_bets"),
            func.sum(Bet.profit).label("total_profit"),
            func.sum(Bet.stake).label("total_wagered"),
            func.count(Bet.id).filter(Bet.profit > 0).label("wins"),
        ).join(
            Sport, Bet.sport_id == Sport.id
        ).where(
            and_(
                Bet.status == "graded",
                Bet.graded_at >= cutoff_date,
                Bet.reason == forecaster
            )
        ).group_by(Sport.name)
        
        results = await self.session.execute(query)
        rows = results.fetchall()
        
        breakdown = []
        for row in rows:
            sport_name, total_bets, total_profit, total_wagered, wins = row
            
            roi = (total_profit / total_wagered * 100) if total_wagered and total_wagered > 0 else 0
            win_rate = (wins / total_bets * 100) if total_bets else 0
            
            breakdown.append({
                "sport": sport_name,
                "bets": int(total_bets),
                "roi": round(roi, 2),
                "win_rate": round(win_rate, 2),
                "profit": float(total_profit or 0),
            })
        
        return sorted(breakdown, key=lambda x: x["roi"], reverse=True)
    
    async def get_win_streak(self, forecaster: str) -> Dict[str, Any]:
        """Get current win/loss streak."""
        query = select(
            Bet.profit,
            Bet.graded_at
        ).where(
            and_(
                Bet.status == "graded",
                Bet.reason == forecaster
            )
        ).order_by(desc(Bet.graded_at)).limit(20)
        
        results = await self.session.execute(query)
        rows = results.fetchall()
        
        if not rows:
            return {"current_streak": 0, "streak_type": "none"}
        
        # Calculate current streak
        streak = 0
        streak_type = "wins" if rows[0][0] > 0 else "losses"
        
        for profit, _ in rows:
            is_win = profit > 0
            if (streak_type == "wins" and is_win) or (streak_type == "losses" and not is_win):
                streak += 1
            else:
                break
        
        return {
            "current_streak": streak,
            "streak_type": streak_type,
            "recent_bets": [{
                "profit": float(p),
                "graded_at": str(d)
            } for p, d in rows]
        }
    
    async def get_contrarian_picks(self, 
                                  forecaster: str,
                                  days: int = 30,
                                  min_roi: float = 10.0) -> List[Dict[str, Any]]:
        """Get forecaster's best contrarian picks (high ROI)."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            Bet.raw_text,
            Bet.stake,
            Bet.profit,
            Bet.odds,
            Bet.placed_at,
            Bet.graded_at,
        ).where(
            and_(
                Bet.status == "graded",
                Bet.graded_at >= cutoff_date,
                Bet.reason == forecaster,
                Bet.profit > 0
            )
        ).order_by(desc(Bet.profit)).limit(20)
        
        results = await self.session.execute(query)
        rows = results.fetchall()
        
        contrarian = []
        for raw_text, stake, profit, odds, placed_at, graded_at in rows:
            roi = (profit / stake * 100) if stake > 0 else 0
            if roi >= min_roi:
                contrarian.append({
                    "bet": raw_text,
                    "stake": float(stake),
                    "profit": float(profit),
                    "roi": round(roi, 2),
                    "odds": float(odds),
                    "placed_at": str(placed_at),
                    "graded_at": str(graded_at),
                })
        
        return contrarian
