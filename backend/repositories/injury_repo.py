from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Injury
class InjuryRepository(BaseRepository[Injury]):
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Injury, session)

    async def get_existing(
        self,
        player_id: str,
        description: str,
        status: str,
    ) -> 'Optional[Injury]':
        stmt = (
            select(Injury)
            .where(
                Injury.player_id == player_id,
                Injury.status == status,
                Injury.description == description,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    async def get_for_player_game(self, player_id, game_id):
        from ..models.injury import Injury
        stmt = select(Injury).where(
            Injury.player_id == player_id,
            Injury.game_id == game_id
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
        """
        Adds an injury record only if an identical one doesn't already exist.
        """
        existing = await self.get_existing(player_id, description, status)
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

    async def list_for_player(
        self,
        player_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[Injury]:
        stmt = (
            select(Injury)
            .where(Injury.player_id == player_id)
            .order_by(Injury.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()