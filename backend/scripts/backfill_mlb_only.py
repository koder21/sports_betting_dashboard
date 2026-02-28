"""
Backfill MLB games and player stats for the last 365 days.
Ensures all games and player stats are inserted, regardless of prior DB state.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from backend.services.scraper_stats import PlayerStatsScraper
from backend.services.espn_client import ESPNClient
from backend.db import get_session
from backend.models.game import Game
from backend.models.games_results import GameResult
from sqlalchemy.dialects.postgresql import insert

async def main() -> None:
    """
    Backfills MLB games and player stats for the last 365 days.
    Ensures all games and player stats are inserted, regardless of prior DB state.
    """
    days_back = 365
    logging.info(f"Starting MLB backfill for last {days_back} days (bypassing last scrape date)...")
    client = ESPNClient()
    async with PlayerStatsScraper.context(client) as scraper:
        async with get_session() as session:
            # Get all completed MLB game IDs for the last 365 days
            game_ids = await scraper._get_recent_game_ids(session, "baseball", "mlb", days_back)
            logging.info(f"Found {len(game_ids)} MLB games to backfill.")
            total_stats = 0
            for idx, game_id in enumerate(game_ids, 1):
                logging.info(f"[{idx}/{len(game_ids)}] Scraping MLB game {game_id}...")
                try:
                    # Upsert minimal games row if missing
                    stmt_game = insert(Game).values(game_id=game_id, sport="MLB", league="mlb").on_conflict_do_nothing(index_elements=["game_id"])
                    await session.execute(stmt_game)
                    # Upsert minimal games_results row if missing
                    stmt_result = insert(GameResult).values(game_id=game_id, sport="MLB", league="mlb").on_conflict_do_nothing(index_elements=["game_id"])
                    await session.execute(stmt_result)
                    await session.commit()
                    stats_count = await scraper._scrape_game_boxscore(session, game_id, "baseball", "mlb", "MLB")
                    await session.commit()
                    logging.info(f"[Boxscore] Saved {stats_count} player stats for game {game_id}")
                    total_stats += stats_count
                except Exception as e:
                    logging.error(f"Failed to process game {game_id}: {e}")
                    await session.rollback()
            logging.info(f"MLB backfill complete: {total_stats} player stat records added.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
