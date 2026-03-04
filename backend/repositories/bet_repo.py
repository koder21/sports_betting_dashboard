from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models import Bet, Game, Player

_ALL_BETS_LIMIT = 10_000  # High ceiling — avoids DEFAULT_LIMIT=100 silently truncating


class BetRepository(BaseRepository[Bet]):
    """
    Bet Repository with optimized relation loading.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Bet, session)

    async def list_pending(
        self,
        *,
        limit: int = _ALL_BETS_LIMIT,
        offset: int = 0,
    ) -> Sequence[Bet]:
        if limit <= 0:
            raise ValueError("Limit must be > 0")

        stmt = (
            select(Bet)
            .where(Bet.status == "pending")
            .options(selectinload(Bet.sport))
            .order_by(Bet.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all_with_relations(
        self,
        *,
        limit: int = _ALL_BETS_LIMIT,
        offset: int = 0,
    ) -> Sequence[Bet]:
        """
        Fetch bets with deep eager loading for Game, Result, Player, Team, and Sport.
        Defaults to _ALL_BETS_LIMIT (not DEFAULT_LIMIT=100) so that all bets are
        returned; results are ordered newest-first so latest pending bets are never
        truncated below older graded bets.
        """
        if limit <= 0:
            raise ValueError("Limit must be > 0")

        stmt = (
            select(Bet)
            .options(
                selectinload(Bet.game).selectinload(Game.result),
                selectinload(Bet.player).selectinload(Player.team),
                selectinload(Bet.sport),
            )
            .order_by(Bet.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_parlay_odds(
        self,
        parlay_id: str,
        parlay_odds: float,
    ) -> int:
        """
        Bulk update odds for a specific parlay ID.
        Returns number of affected bets.
        """
        stmt = (
            update(Bet)
            .where(Bet.parlay_id == parlay_id)
            .values(parlay_odds=parlay_odds)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(stmt)
        count = getattr(result, "rowcount", None)
        if count is None:
            count_stmt = select(Bet).where(Bet.parlay_id == parlay_id)
            count_result = await self.session.execute(count_stmt)
            count = len(count_result.scalars().all())
        return count