"""
Backfill NHL games and player stats for the last 180 days.
Ensures all games and player stats are inserted, regardless of prior DB state.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from backend.services.scraper_stats import PlayerStatsScraper
from backend.services.espn_client import ESPNClient
from backend.db import get_session
from backend.models.game import Game
from backend.models.games_results import GameResult
from sqlalchemy.dialects.postgresql import insert


async def main():
    days_back = 180
    print(f"Starting NHL backfill for last {days_back} days (bypassing last scrape date)...")
    client = ESPNClient()
    async with PlayerStatsScraper.context(client) as scraper:
        async with get_session() as session:
            # Get all completed NHL game IDs for the last 180 days
            game_ids = await scraper._get_recent_game_ids(session, "hockey", "nhl", days_back)
            print(f"Found {len(game_ids)} NHL games to backfill.")
            total_stats = 0
            for idx, game_id in enumerate(game_ids, 1):
                print(f"[{idx}/{len(game_ids)}] Scraping NHL game {game_id}...")
                try:
                    # Upsert minimal games row if missing
                    stmt_game = insert(Game).values(game_id=game_id, sport="NHL", league="nhl").on_conflict_do_nothing(index_elements=["game_id"])
                    await session.execute(stmt_game)
                    # Upsert minimal games_results row if missing
                    stmt_result = insert(GameResult).values(game_id=game_id, sport="NHL", league="nhl").on_conflict_do_nothing(index_elements=["game_id"])
                    await session.execute(stmt_result)
                    await session.commit()
                    stats_count = await scraper._scrape_game_boxscore(session, game_id, "hockey", "nhl", "NHL")
                    await session.commit()
                    print(f"[Boxscore] Saved {stats_count} player stats for game {game_id}")
                    total_stats += stats_count
                except Exception as e:
                    print(f"[Error] Failed to process game {game_id}: {e}")
                    await session.rollback()
            print(f"NHL backfill complete: {total_stats} player stat records added.")

if __name__ == "__main__":
    asyncio.run(main())
