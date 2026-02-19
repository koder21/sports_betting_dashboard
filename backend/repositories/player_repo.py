from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Player


class PlayerRepository(BaseRepository[Player]):
    """
    Repository for Player entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Player, session)

    async def get_by_espn(
        self,
        espn_id: str,
        team_id: Optional[str],
    ) -> 'Optional[Player]':
        stmt = select(Player).where(Player.espn_id == espn_id).limit(1)

        if team_id is not None:
            stmt = stmt.where(Player.team_id == team_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_team(
        self,
        team_id: str,
        *,
        limit: int = 200,
    ) -> Sequence[Player]:
        stmt = (
            select(Player)
            .where(Player.team_id == team_id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_by_name(
        self,
        name: str,
        *,
        limit: int = 5,
    ) -> Sequence[Player]:
        """
        Case-insensitive partial match search.
        """
        if not name:
            return []

        term = f"%{name.strip()}%"
        stmt = (
            select(Player)
            .where(
                or_(
                    Player.full_name.ilike(term),
                    Player.name.ilike(term),
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(
        self,
        espn_id: str,
        name: str,
        position: Optional[str],
        team_id: Optional[str],
        season_stats_json: Optional[dict] = None,
        espn_ref: Optional[str] = None,
    ) -> Player:
        """
        Creates or updates a player based on ESPN ID.
        """
        player = await self.get_by_espn(espn_id, team_id)

        updates = {
            "full_name": name,
            "name": name,
            "position": position,
            "season_stats_json": season_stats_json,
            "espn_ref": espn_ref,
        }
        # Only include team_id if it's explicitly provided, otherwise keep existing
        if team_id is not None:
            updates["team_id"] = team_id

        if not player:
            # Create new
            player = Player(
                player_id=espn_id,
                espn_id=espn_id,
                **updates
            )
            self.session.add(player)
        else:
            # Update existing only if changed
            for key, val in updates.items():
                if val is not None and getattr(player, key) != val:
                    setattr(player, key, val)

        await self.session.flush()
        return player