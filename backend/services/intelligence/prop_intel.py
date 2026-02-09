from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.player_stat_repo import PlayerStatRepository
from ...repositories.player_repo import PlayerRepository


class PropIntelligenceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats = PlayerStatRepository(session)
        self.players = PlayerRepository(session)

    async def suggest_prop(self, player_id: int, market: str) -> Optional[Dict[str, Any]]:
        player = await self.players.get(player_id)
        if not player:
            return None

        history = await self.stats.list_for_player(player_id)
        if not history:
            return None

        values = []
        for h in history:
            val = getattr(h, market, None)
            if val is not None:
                values.append(val)

        if not values:
            return None

        avg = sum(values) / len(values)

        return {
            "player": player.name,
            "market": market,
            "projection": avg,
            "confidence": min(100, max(0, int((len(values) / 10) * 100))),
        }