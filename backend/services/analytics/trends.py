from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.bet_repo import BetRepository


class TrendAnalytics:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)

    async def win_loss_trend(self) -> Dict[str, Any]:
        all_bets = await self.bets.list_all()

        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                parlays_by_id[b.parlay_id].append(b)
        
        wins = 0
        losses = 0
        pending = 0
        pushes = 0
        voids = 0
        
        # Determine status for each bet (parlay or single)
        for parlay_id, legs in parlays_by_id.items():
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            if pending_legs:
                pending += 1
            elif all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                wins += 1
            elif any(l.status == "lost" for l in legs):
                losses += 1
            elif all(l.status == "void" for l in legs):
                voids += 1
            elif all(l.status in ["push", "void"] for l in legs):
                pushes += 1
            else:
                # Mixed void/push situation - treat as push
                pushes += 1

        return {
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "pushes": pushes,
            "voids": voids,
        }

    async def by_market(self) -> Dict[str, Any]:
        all_bets = await self.bets.list_all()

        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                parlays_by_id[b.parlay_id].append(b)
        
        markets: Dict[str, Dict[str, int]] = {}

        # Determine status for each bet and count by market
        for parlay_id, legs in parlays_by_id.items():
            # Use the market from the first leg (all legs in a parlay should have same market ideally)
            m = legs[0].market or "other"
            if m not in markets:
                markets[m] = {"won": 0, "lost": 0, "push": 0, "void": 0, "pending": 0}
            
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            if pending_legs:
                markets[m]["pending"] += 1
            elif all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                markets[m]["won"] += 1
            elif any(l.status == "lost" for l in legs):
                markets[m]["lost"] += 1
            elif all(l.status == "void" for l in legs):
                markets[m]["void"] += 1
            else:
                markets[m]["push"] += 1

        return markets

    async def streak_analysis(self) -> Dict[str, Any]:
        """Calculate current and longest win/loss streaks"""
        all_bets = await self.bets.list_all_with_relations()
        
        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        parlay_dates = {}
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                    parlay_dates[b.parlay_id] = b.placed_at or b.created_at
                parlays_by_id[b.parlay_id].append(b)
        
        # Determine status for each bet and sort by date
        bet_statuses = []
        for parlay_id, legs in parlays_by_id.items():
            graded_legs = [l for l in legs if l.status in ["won", "lost", "push", "void"]]
            pending_legs = [l for l in legs if l.status == "pending"]
            
            status = None
            if pending_legs:
                status = "pending"
            elif all(l.status == "won" for l in graded_legs) and len(graded_legs) == len(legs):
                status = "won"
            elif any(l.status == "lost" for l in legs):
                status = "lost"
            else:
                status = "other"  # push/void
            
            if status in ["won", "lost"]:  # Only count graded bets for streaks
                bet_statuses.append({
                    "status": status,
                    "date": parlay_dates.get(parlay_id)
                })
        
        # Sort by date
        bet_statuses.sort(key=lambda x: x["date"] or "", reverse=True)
        
        # Calculate streaks
        current_win_streak = 0
        current_loss_streak = 0
        longest_win_streak = 0
        longest_loss_streak = 0
        
        for bet in bet_statuses:
            if bet["status"] == "won":
                current_win_streak += 1
                current_loss_streak = 0
                longest_win_streak = max(longest_win_streak, current_win_streak)
            elif bet["status"] == "lost":
                current_loss_streak += 1
                current_win_streak = 0
                longest_loss_streak = max(longest_loss_streak, current_loss_streak)
        
        return {
            "current_win_streak": current_win_streak,
            "current_loss_streak": current_loss_streak,
            "longest_win_streak": longest_win_streak,
            "longest_loss_streak": longest_loss_streak
        }