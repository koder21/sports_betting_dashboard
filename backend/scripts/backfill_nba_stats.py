"""
NBA Backfill Script
------------------
Fetches and upserts NBA game and player stats for the last 180 days into Postgres.
This script is intended for one-time use after migration to Postgres.
"""
import asyncio
from datetime import datetime, timedelta

from backend.services.scraper_stats import scrape_nba_game_stats
from backend.db import async_session
from backend.repositories.games import upsert_game
from backend.repositories.player_stats import upsert_player_stats

# You may need to adjust these imports based on your project structure

async def get_nba_game_ids_for_backfill():
    """
    Fetch all NBA game IDs for the last 180 days from an external API or your own logic.
    This is a placeholder: replace with your actual NBA schedule/game ID fetch logic.
    """
    # Example: Use ESPN API, NBA API, or your own endpoint
    # For now, just return an empty list (to be implemented)
    return []

async def backfill_nba_stats():
    days = 180
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)
    print(f"Backfilling NBA games from {start_date} to {today}")

    # 1. Get all NBA game IDs for the last 180 days
    game_ids = await get_nba_game_ids_for_backfill()
    print(f"Found {len(game_ids)} NBA games to backfill.")

    # 2. For each game, scrape and upsert stats
    for idx, game_id in enumerate(game_ids):
        print(f"[{idx+1}/{len(game_ids)}] Scraping NBA game {game_id}...")
        try:
            # Use your robust NBA scraping logic
            stats = await scrape_nba_game_stats(game_id)
            if not stats:
                print(f"No stats found for game {game_id}")
                continue
            # Upsert game and player stats
            async with async_session() as session:
                await upsert_game(session, stats['game'])
                for player_stat in stats['player_stats']:
                    await upsert_player_stats(session, player_stat)
                await session.commit()
            print(f"Game {game_id} upserted.")
        except Exception as e:
            print(f"Error scraping game {game_id}: {e}")

if __name__ == "__main__":
    asyncio.run(backfill_nba_stats())
