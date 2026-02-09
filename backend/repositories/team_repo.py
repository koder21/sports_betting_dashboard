from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import BaseRepository
from .sport_repo import SportRepository
from ..models import Team, Sport


class TeamRepository(BaseRepository[Team]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Team)

    async def get_by_espn_id(self, espn_id: str) -> Optional[Team]:
        """Get team by ESPN id (same as team_id)."""
        return await self.get(espn_id)

    async def get_by_espn(self, espn_id: str, sport_id: Optional[int] = None) -> Optional[Team]:
        stmt = select(Team).where(Team.espn_id == espn_id)
        if sport_id is not None:
            stmt = stmt.where(Team.sport_id == sport_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_sport(self, sport_id: int) -> Sequence[Team]:
        stmt = select(Team).where(Team.sport_id == sport_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(
        self,
        espn_id: str,
        name: str,
        sport_id: int,
        record: Optional[str] = None,
        stats_json: Optional[dict] = None,
    ) -> Team:
        team = await self.get_by_espn(espn_id)
        if not team:
            team = Team(
                team_id=espn_id,
                espn_id=espn_id,
                name=name,
                sport_id=sport_id,
                record=record or "",
                stats_json=stats_json,
            )
            self.session.add(team)
        else:
            team.name = name
            if record is not None:
                team.record = record
            if stats_json is not None:
                team.stats_json = stats_json

        await self.session.flush()
        return team

    async def get_or_create_sport(self, name: str, league: Optional[str]) -> Sport:
        """Delegate to SportRepository for get_or_create by name/league."""
        sport_repo = SportRepository(self.session)
        return await sport_repo.get_or_create_by_name_and_league(name, league)
