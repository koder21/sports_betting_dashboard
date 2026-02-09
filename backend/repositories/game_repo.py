from typing import Optional, Sequence
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import BaseRepository
from ..models import Game


class GameRepository(BaseRepository[Game]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Game)

    async def get_by_espn(self, espn_id: str, sport_id: Optional[int] = None) -> Optional[Game]:
        """Get game by ESPN id (game_id). sport_id optional filter."""
        stmt = select(Game).where(Game.game_id == espn_id)
        if sport_id is not None:
            stmt = stmt.where(Game.sport_id == sport_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_teams_and_date(
        self,
        sport_id: int,
        home_team_id: str,
        away_team_id: str,
        target_date: datetime,
        tolerance_days: int = 1,
    ) -> Optional[Game]:
        start = target_date - timedelta(days=tolerance_days)
        end = target_date + timedelta(days=tolerance_days)
        stmt = (
            select(Game)
            .where(
                Game.sport_id == sport_id,
                Game.home_team_id == home_team_id,
                Game.away_team_id == away_team_id,
                Game.start_time >= start,
                Game.start_time <= end,
            )
            .order_by(Game.start_time.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_date_range(
        self,
        sport_id: int,
        start: datetime,
        end: datetime,
    ) -> Sequence[Game]:
        stmt = select(Game).where(
            Game.sport_id == sport_id,
            Game.start_time >= start,
            Game.start_time <= end,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_upcoming(self) -> Sequence[Game]:
        now = datetime.utcnow()
        stmt = (
            select(Game)
            .where(
                Game.start_time > now,
                Game.status == "upcoming",
            )
            .order_by(Game.start_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_from_payload(self, data: dict) -> Game:
        """Upsert using a payload with game_id (or espn_id) and optional sport_id."""
        game_id = data.get("game_id") or data.get("espn_id")
        if not game_id:
            raise ValueError("payload must have game_id or espn_id")
        sport_id = data.get("sport_id")
        game = await self.get_by_espn(str(game_id), sport_id)

        if not game:
            game = Game(**{k: v for k, v in data.items() if hasattr(Game, k)})
            if not game.game_id:
                game.game_id = str(game_id)
            self.session.add(game)
        else:
            for k, v in data.items():
                if hasattr(Game, k):
                    setattr(game, k, v)

        await self.session.flush()
        return game

    async def upsert(self, game_data: dict) -> Game:
        """Normalize scraper payload (espn_id, date, int ids) and upsert."""
        from datetime import datetime as dt

        data = dict(game_data)
        data["game_id"] = data.get("game_id") or data.get("espn_id")
        if not data["game_id"]:
            raise ValueError("game_data must have game_id or espn_id")

        date_val = data.get("date")
        if date_val is not None and isinstance(date_val, dt):
            data["start_time"] = date_val
        elif data.get("start_time") is None and "date" in data:
            # attempt to parse if string
            try:
                data["start_time"] = dt.fromisoformat(str(data["date"]))
            except Exception:
                data["start_time"] = None
        data.pop("date", None)
        data.pop("espn_id", None)

        for key in ("home_team_id", "away_team_id"):
            if key in data and data[key] is not None:
                data[key] = str(data[key])

        status = data.get("status", "")
        if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
            data["status"] = "final"
        elif status and not data.get("status"):
            data["status"] = status

        return await self.upsert_from_payload(data)
