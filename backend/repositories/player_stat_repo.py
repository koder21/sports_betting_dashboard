from typing import Optional, Sequence, Iterable, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import PlayerStat


class PlayerStatRepository(BaseRepository[PlayerStat]):
    """
    Optimizations:
    - LIMIT 1 for single-row lookup
    - Added limits to unbounded list queries
    - Session sync for bulk deletes
    - Batch insert for bulk replace
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PlayerStat, session)

    async def get_for_player_game(
        self,
        player_id: str,
        game_id: str,
    ) -> Optional[PlayerStat]:

        stmt = (
            select(PlayerStat)
            .where(
                PlayerStat.player_id == player_id,
                PlayerStat.game_id == game_id,
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_player(
        self,
        player_id: str,
        *,
        limit: int = 200,
    ) -> Sequence[PlayerStat]:

        stmt = (
            select(PlayerStat)
            .where(PlayerStat.player_id == player_id)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_game(
        self,
        game_id: str,
        *,
        limit: int = 500,
    ) -> Sequence[PlayerStat]:

        stmt = (
            select(PlayerStat)
            .where(PlayerStat.game_id == game_id)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        player_id: str,
        game_id: str,
        stats_json: dict,
    ) -> PlayerStat:

        stmt = (
            select(PlayerStat)
            .where(
                PlayerStat.player_id == player_id,
                PlayerStat.game_id == game_id,
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.stats_json = stats_json
            await self.session.flush()
            return existing

        new_stat = PlayerStat(
            player_id=player_id,
            game_id=game_id,
            stats_json=stats_json,
        )
        self.session.add(new_stat)
        await self.session.flush()
        return new_stat

    async def bulk_replace_for_game(
        self,
        game_id: str,
        stats_list: Iterable[dict],
    ) -> None:

        await self.session.execute(
            delete(PlayerStat)
            .where(PlayerStat.game_id == game_id)
            .execution_options(synchronize_session="fetch")
        )

        objects: List[PlayerStat] = [
            PlayerStat(
                player_id=entry["player_id"],
                game_id=game_id,
                stats_json=entry.get("stats_json"),
            )
            for entry in stats_list
        ]

        if objects:
            self.session.add_all(objects)

        await self.session.flush()

    async def delete_for_game(self, game_id: str) -> None:
        await self.session.execute(
            delete(PlayerStat)
            .where(PlayerStat.game_id == game_id)
            .execution_options(synchronize_session="fetch")
        )

    async def delete_for_player(self, player_id: str) -> None:
        await self.session.execute(
            delete(PlayerStat)
            .where(PlayerStat.player_id == player_id)
            .execution_options(synchronize_session="fetch")
        )