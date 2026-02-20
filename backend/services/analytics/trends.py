from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from backend.db import get_session

from ...repositories.bet_repo import BetRepository


class TrendAnalytics:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.bets = BetRepository(session) if session else None

    async def win_loss_trend(self) -> Dict[str, Any]:
        if self.session is None:
            async with get_session() as session:
                bets = BetRepository(session)
                all_bets = await bets.list_all_with_relations()
        else:
            all_bets = await self.bets.list_all_with_relations()

        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        singles = []
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                parlays_by_id[b.parlay_id].append(b)
            else:
                singles.append(b)
        
        # Separate 1-leg parlays into singles (treat as singles, not parlays)
        one_leg_parlays = [pid for pid, legs in parlays_by_id.items() if len(legs) == 1]
        for pid in one_leg_parlays:
            singles.extend(parlays_by_id[pid])
            del parlays_by_id[pid]
        
        wins = 0
        losses = 0
        pending = 0
        pushes = 0
        voids = 0
        
        # Determine status for each multi-leg parlay
        for parlay_id, legs in parlays_by_id.items():
            if legs[0].original_stake is None:
                continue
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
        
        # Add singles to the counts
        for bet in singles:
            if bet.status == "won":
                wins += 1
            elif bet.status == "lost":
                losses += 1
            elif bet.status == "pending":
                pending += 1
            elif bet.status == "void":
                voids += 1
            elif bet.status == "push":
                pushes += 1

        return {
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "pushes": pushes,
            "voids": voids,
        }

    async def by_market(self) -> Dict[str, Any]:
        if self.session is None:
            async with get_session() as session:
                bets = BetRepository(session)
                all_bets = await bets.list_all_with_relations()
        else:
            all_bets = await self.bets.list_all_with_relations()

        # Group by parlay_id to count bets, not legs
        parlays_by_id = {}
        singles = []
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                parlays_by_id[b.parlay_id].append(b)
            else:
                singles.append(b)
        
        # Separate 1-leg parlays into singles (treat as singles, not parlays)
        one_leg_parlays = [pid for pid, legs in parlays_by_id.items() if len(legs) == 1]
        for pid in one_leg_parlays:
            singles.extend(parlays_by_id[pid])
            del parlays_by_id[pid]
        
        markets: Dict[str, Dict[str, int]] = {}

        # Determine status for each multi-leg parlay and count by market
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
        
        # Add singles to market counts
        for bet in singles:
            m = bet.market or "other"
            if m not in markets:
                markets[m] = {"won": 0, "lost": 0, "push": 0, "void": 0, "pending": 0}
            
            if bet.status == "won":
                markets[m]["won"] += 1
            elif bet.status == "lost":
                markets[m]["lost"] += 1
            elif bet.status == "pending":
                markets[m]["pending"] += 1
            elif bet.status == "void":
                markets[m]["void"] += 1
            elif bet.status == "push":
                markets[m]["push"] += 1

        return markets

    async def streak_analysis(self) -> Dict[str, Any]:
        """Calculate current and longest win/loss streaks"""
        if self.session is None:
            async with get_session() as session:
                bets = BetRepository(session)
                all_bets = await bets.list_all_with_relations()
        else:
            all_bets = await self.bets.list_all_with_relations()
        
        # Group bets by parlay_id (multi-leg parlays) and singles
        parlays_by_id = {}
        parlay_dates = {}
        singles = []
        for b in all_bets:
            if b.parlay_id:
                if b.parlay_id not in parlays_by_id:
                    parlays_by_id[b.parlay_id] = []
                    parlay_dates[b.parlay_id] = b.placed_at or b.created_at
                parlays_by_id[b.parlay_id].append(b)
            else:
                singles.append(b)

        # Only count grouped bets (multi-leg parlays and singles)
        bet_statuses = []

        # Multi-leg parlays: count as one grouped bet
        for parlay_id, legs in parlays_by_id.items():
            if len(legs) == 1:
                # Treat 1-leg parlays as singles
                singles.append(legs[0])
                continue
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
            if status in ["won", "lost"]:
                bet_statuses.append({
                    "status": status,
                    "date": parlay_dates.get(parlay_id)
                })

        # Singles: count as one grouped bet each
        for bet in singles:
            if bet.status in ["won", "lost"]:
                bet_statuses.append({
                    "status": bet.status,
                    "date": bet.placed_at or bet.created_at
                })

        # Sort by date (most recent first)
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