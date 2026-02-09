from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import BaseRepository
from ..models import Injury


class InjuryRepository(BaseRepository[Injury]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Injury)

    async def get_existing(
        self,
        player_id: str,
        description: str,
        status: str,
    ) -> Optional[Injury]:
        stmt = select(Injury).where(
            Injury.player_id == player_id,
            Injury.status == status,
            Injury.description == description,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_if_new(
        self,
        player_id: str,
        team_id: str,
        description: str,
        status: str,
    ) -> Injury:
        existing = await self.get_existing(
            player_id=player_id,
            description=description,
            status=status,
        )
        if existing:
            return existing

        injury = Injury(
            player_id=player_id,
            team_id=team_id,
            description=description,
            status=status,
        )
        self.session.add(injury)
        await self.session.flush()
        return injury

    async def list_for_player(self, player_id: str) -> Sequence[Injury]:
        stmt = select(Injury).where(Injury.player_id == player_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()