from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .base import BaseRepository
from ..models import Player


class PlayerRepository(BaseRepository[Player]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Player)

    async def get_by_espn(
        self,
        espn_id: str,
        team_id: Optional[str],
    ) -> Optional[Player]:
        stmt = select(Player).where(Player.espn_id == espn_id)
        if team_id is not None:
            stmt = stmt.where(Player.team_id == team_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_espn_and_team(self, espn_id: str, team_id: Optional[str]) -> Optional[Player]:
        """Alias for get_by_espn(espn_id, team_id)."""
        return await self.get_by_espn(espn_id, team_id)

    async def list_by_team(self, team_id: str) -> Sequence[Player]:
        stmt = select(Player).where(Player.team_id == team_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_by_name(self, name: str) -> Optional[Player]:
        """Search for a player by name (full_name or name)"""
        name_lower = name.lower().strip()
        stmt = select(Player).where(
            (func.lower(Player.full_name).ilike(f"%{name_lower}%")) |
            (func.lower(Player.name).ilike(f"%{name_lower}%"))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        espn_id: str,
        name: str,
        position: Optional[str],
        team_id: Optional[str],
        season_stats_json: Optional[dict] = None,
        espn_ref: Optional[str] = None,
    ) -> Player:
        player = await self.get_by_espn(espn_id, team_id)
        if not player:
            player = Player(
                player_id=espn_id,
                espn_id=espn_id,
                full_name=name,
                name=name,
                position=position,
                team_id=team_id,
                season_stats_json=season_stats_json,
                espn_ref=espn_ref,
            )
            self.session.add(player)
        else:
            player.full_name = name
            player.name = name
            player.position = position
            if season_stats_json is not None:
                player.season_stats_json = season_stats_json
            if espn_ref is not None:
                player.espn_ref = espn_ref

        await self.session.flush()
        return player
