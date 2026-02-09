from typing import Optional, Sequence, Iterable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .base import BaseRepository
from ..models import PlayerStat


class PlayerStatRepository(BaseRepository[PlayerStat]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PlayerStat)

    async def get_for_player_game(
        self,
        player_id: str,
        game_id: str,
    ) -> Optional[PlayerStat]:
        stmt = select(PlayerStat).where(
            PlayerStat.player_id == player_id,
            PlayerStat.game_id == game_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_player(self, player_id: str) -> Sequence[PlayerStat]:
        stmt = select(PlayerStat).where(PlayerStat.player_id == player_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_game(self, game_id: str) -> Sequence[PlayerStat]:
        stmt = select(PlayerStat).where(PlayerStat.game_id == game_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(
        self,
        player_id: str,
        game_id: str,
        stats_json: dict,
    ) -> PlayerStat:
        existing = await self.get_for_player_game(player_id, game_id)
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
            delete(PlayerStat).where(PlayerStat.game_id == game_id)
        )

        for entry in stats_list:
            stat = PlayerStat(
                player_id=entry["player_id"],
                game_id=entry["game_id"],
                stats_json=entry.get("stats_json"),
            )
            self.session.add(stat)
        await self.session.flush()

    async def delete_for_game(self, game_id: str) -> None:
        await self.session.execute(
            delete(PlayerStat).where(PlayerStat.game_id == game_id)
        )

    async def delete_for_player(self, player_id: str) -> None:
        await self.session.execute(
            delete(PlayerStat).where(PlayerStat.player_id == player_id)
        )
