from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from .sport_repo import SportRepository
from ..models import Team, Sport


class TeamRepository(BaseRepository[Team]):
    """
    Optimizations:
    - LIMIT 1 for single-row queries
    - Added limits for list queries
    - Avoided redundant updates
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Team, session)

    async def get_by_espn_id(self, espn_id: str) -> Optional[Team]:
        return await self.get(espn_id)

    async def get_by_espn(
        self,
        espn_id: str,
        sport_id: Optional[int] = None,
    ) -> Optional[Team]:

        stmt = (
            select(Team)
            .where(Team.espn_id == espn_id)
            .limit(1)
        )

        if sport_id is not None:
            stmt = stmt.where(Team.sport_id == sport_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_sport(
        self,
        sport_id: int,
        *,
        limit: int = 200,
    ) -> Sequence[Team]:

        stmt = (
            select(Team)
            .where(Team.sport_id == sport_id)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        espn_id: str,
        name: str,
        sport_id: int,
        record: Optional[str] = None,
        stats_json: Optional[dict] = None,
    ) -> Team:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        values = dict(
            team_id=espn_id,
            espn_id=espn_id,
            name=name,
            sport_id=sport_id,
            record=record or "",
            stats_json=stats_json,
        )
        stmt = pg_insert(Team).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["team_id"])
        await self.session.execute(stmt)
        # Now fetch the team (guaranteed to exist)
        team = await self.get_by_espn(espn_id, sport_id)
        # Update fields if needed
        updated = False
        if team:
            if team.name != name:
                team.name = name
                updated = True
            if record is not None and team.record != record:
                team.record = record
                updated = True
            if stats_json is not None and team.stats_json != stats_json:
                team.stats_json = stats_json
                updated = True
            if updated:
                await self.session.flush()
        return team

    async def get_or_create_sport(
        self,
        name: str,
        league: Optional[str],
    ) -> Sport:

        sport_repo = SportRepository(self.session)
        return await sport_repo.get_or_create_by_name_and_league(name, league)