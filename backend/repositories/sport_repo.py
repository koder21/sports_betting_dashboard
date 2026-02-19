from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Sport


class SportRepository(BaseRepository[Sport]):
    """
    Optimizations:
    - LIMIT 1 for lookups
    - Reduced duplicate queries
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Sport, session)

    async def get_by_league_code(self, code: str) -> Optional[Sport]:

        stmt = (
            select(Sport)
            .where(Sport.espn_league_code == code)
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_by_name_and_league(
        self,
        name: str,
        league: Optional[str],
    ) -> Sport:

        code = league or name

        stmt = (
            select(Sport)
            .where(Sport.espn_league_code == code)
            .limit(1)
        )

        result = await self.session.execute(stmt)
        sport = result.scalar_one_or_none()
        if sport:
            return sport

        sport = Sport(
            name=name,
            espn_league_code=code,
            league=league,
        )
        self.session.add(sport)
        await self.session.flush()
        return sport