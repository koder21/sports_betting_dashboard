from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Game
from ..utils.json import normalize_json_payload


class GameRepository(BaseRepository[Game]):
    """
    Repository for Game entities with specialized upsert and JSON handling.
    """

    JSON_FIELDS = {
        "lines_json",
        "odds_history_json",
        "play_by_play_json",
        "boxscore_json",
        "head_to_head_json",
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Game, session)
        # Cache column names for fast validation
        self._valid_columns = set(Game.__table__.columns.keys())

    async def get_by_espn(
        self,
        espn_id: str,
        sport_id: Optional[int] = None,
    ) -> 'Optional[Game]':
        stmt = select(Game).where(Game.game_id == espn_id).limit(1)

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
    ) -> 'Optional[Game]':
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
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_upcoming(self, *, limit: int = 200) -> Sequence[Game]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Game)
            .where(
                Game.start_time > now,
                Game.status == "upcoming",
            )
            .order_by(Game.start_time.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, game_data: dict[str, Any]) -> Game:
        """
        High-level upsert that normalizes input data before persistence.
        """
        # Create a copy to avoid mutating the original input
        data = game_data.copy()

        # 1. Resolve Game ID
        game_id = data.get("game_id") or data.get("espn_id")
        if not game_id:
            raise ValueError("Payload must contain 'game_id' or 'espn_id'")
        
        # Ensure ID is string and stored in the primary field
        data["game_id"] = str(game_id)
        # Remove alias to prevent keyword argument errors
        data.pop("espn_id", None) 

        # 2. Normalize Dates
        date_val = data.pop("date", None)
        if date_val and not data.get("start_time"):
            if isinstance(date_val, datetime):
                data["start_time"] = date_val
            else:
                try:
                    data["start_time"] = datetime.fromisoformat(str(date_val))
                except (ValueError, TypeError):
                    data["start_time"] = None

        # 3. Normalize JSON Fields
        for key in self.JSON_FIELDS:
            if key in data:
                data[key] = normalize_json_payload(data[key])

        # 4. Normalize Status
        status = data.get("status")
        if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
            data["status"] = "final"
        
        # 5. Type Cast IDs
        for key in ("home_team_id", "away_team_id", "sport_id"):
             if key in data and data[key] is not None:
                 # sport_id is int, others are str usually
                 if key == "sport_id":
                     data[key] = int(data[key])
                 else:
                     data[key] = str(data[key])

        return await self._perform_upsert(data)

    async def _perform_upsert(self, clean_data: dict[str, Any]) -> Game:
        """
        Internal method to execute the upsert on the database.
        """
        game_id = clean_data["game_id"]
        sport_id = clean_data.get("sport_id")

        # Check existence
        existing_game = await self.get_by_espn(game_id, sport_id)

        # Filter dictionary to only include keys that exist in the model
        valid_payload = {
            k: v for k, v in clean_data.items() 
            if k in self._valid_columns
        }

        if not existing_game:
            new_game = Game(**valid_payload)
            self.session.add(new_game)
            # Flush is used here to generate the primary key (id) if other
            # operations immediately rely on it.
            await self.session.flush()
            return new_game
        else:
            # Update existing instance
            for key, value in valid_payload.items():
                if getattr(existing_game, key) != value:
                    setattr(existing_game, key, value)
            
            # No flush needed unless requested by caller, but generally safe to wait for commit
            return existing_game