"""
NFL Backfill Script
------------------
This script backfills NFL game and player stats for the last 180 days, similar to the NBA backfill script.
It ensures all games and player stats are inserted, upserting minimal games and games_results rows as needed.
"""

"""
NFL-Only Backfill Script
-----------------------
Fetches and upserts NFL game and player stats for the last 180 days into Postgres.
This script is intended for one-time use after migration to Postgres.
"""
import asyncio
from backend.services.scraper_stats import PlayerStatsScraper, ESPNClient

async def main():
    print("Starting NFL backfill for last 180 days (bypassing last scrape date)...")
    stats_scraper = PlayerStatsScraper(ESPNClient())
    stats_scraper.SPORTS_CONFIG = [("football", "nfl", "NFL")]
    from backend.db import get_session
    async with get_session() as session:
        # Always fetch all NFL game IDs for the last 180 days
        game_ids = await stats_scraper._get_recent_game_ids(session, "football", "nfl", 180)
        print(f"Found {len(game_ids)} NFL games to backfill.")
        total_stats = 0
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from backend.models.games_results import GameResult
        from backend.models.game import Game
        for idx, game_id in enumerate(game_ids):
            print(f"[{idx+1}/{len(game_ids)}] Scraping NFL game {game_id}...")
            # 1. Ensure games and games_results row exist (minimal upsert if missing)
            try:
                # Ensure games row exists
                game_row = await session.execute(select(Game).where(Game.game_id == game_id))
                game_exists = game_row.scalar_one_or_none()
                if not game_exists:
                    await session.execute(
                        pg_insert(Game).values(
                            game_id=game_id,
                            sport="NFL",
                            league="nfl",
                            start_time=None,
                            home_team_id=None,
                            away_team_id=None,
                            home_team_name=None,
                            away_team_name=None,
                            status=None,
                        ).on_conflict_do_nothing(index_elements=['game_id'])
                    )
                    await session.commit()
                # Ensure games_results row exists
                result = await session.execute(select(GameResult).where(GameResult.game_id == game_id))
                exists = result.scalar_one_or_none()
                if not exists:
                    await session.execute(
                        pg_insert(GameResult).values(
                            game_id=game_id,
                            sport="NFL",
                            league="nfl",
                            start_time=None,
                            home_team_id=None,
                            away_team_id=None,
                            home_team_name=None,
                            away_team_name=None,
                            status=None,
                        ).on_conflict_do_nothing(index_elements=['game_id'])
                    )
                    await session.commit()
            except Exception as e:
                print(f"[Upsert] Exception ensuring games/games_results for game {game_id}: {e}")
                await session.rollback()
                continue

            # 2. Now insert player_stats for this game
            try:
                stats_count = await stats_scraper._scrape_game_boxscore(session, game_id, "football", "nfl", "NFL")
                print(f"[Boxscore] Saved {stats_count} player stats for game {game_id}")
            except Exception as e:
                print(f"[Boxscore] Error saving player stats for game {game_id}: {e}")
        print(f"NFL backfill complete: {total_stats} player stat records added.")

if __name__ == "__main__":
    asyncio.run(main())
