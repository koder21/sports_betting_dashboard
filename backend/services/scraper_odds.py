from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from backend.models.game import Game
from backend.models.games_upcoming import GameUpcoming

async def upsert_odds(session: AsyncSession, game_id: str, odds: Optional[Dict[str, Any]]):
    """
    Upsert odds/lines JSON into the Game and GameUpcoming tables for a given game_id.
    odds: dict from ESPN odds endpoint (raw)
    """
    if not odds or not game_id:
        return
    # Store full odds JSON in Game table
    await session.execute(
        insert(Game)
        .values(game_id=game_id, lines_json=odds)
        .on_conflict_do_update(
            index_elements=["game_id"],
            set_={"lines_json": odds}
        )
    )
    # Optionally, extract and store key fields in GameUpcoming
    # (e.g., moneyline, spread, total)
    try:
        home_ml = away_ml = spread_home = spread_away = total = None
        if "items" in odds and odds["items"]:
            for item in odds["items"]:
                if item.get("type") == "moneyline":
                    home_ml = item.get("home")
                    away_ml = item.get("away")
                elif item.get("type") == "spread":
                    spread_home = item.get("home")
                    spread_away = item.get("away")
                elif item.get("type") == "total":
                    total = item.get("value")
        await session.execute(
            insert(GameUpcoming)
            .values(
                game_id=game_id,
                odds_home=home_ml,
                odds_away=away_ml,
                spread_home=spread_home,
                spread_away=spread_away,
                total=total,
            )
            .on_conflict_do_update(
                index_elements=["game_id"],
                set_={
                    "odds_home": home_ml,
                    "odds_away": away_ml,
                    "spread_home": spread_home,
                    "spread_away": spread_away,
                    "total": total,
                }
            )
        )
    except Exception:
        pass
    await session.commit()
