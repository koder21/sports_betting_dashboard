from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models import Bet


class BetRepository(BaseRepository[Bet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Bet)

    async def list_pending(self) -> Sequence[Bet]:
        stmt = select(Bet).where(Bet.status == "pending")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all(self) -> Sequence[Bet]:
        result = await self.session.execute(select(Bet))
        return result.scalars().all()

    async def list_all_with_relations(self) -> Sequence[Bet]:
        """List all bets with eager-loaded game, player, and sport relationships"""
        from ..models.player import Player
        from ..models.game import Game
        
        stmt = select(Bet).options(
            selectinload(Bet.game).selectinload(Game.result),
            selectinload(Bet.player).selectinload(Player.team),
            selectinload(Bet.sport)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_parlay_odds(self, parlay_id: str, parlay_odds: float) -> None:
        """Update parlay_odds for all bets in a parlay"""
        stmt = update(Bet).where(Bet.parlay_id == parlay_id).values(parlay_odds=parlay_odds)
        await self.session.execute(stmt)