
"""
EPL-Only Backfill Script
-------------------------
Fetches and upserts EPL game and player stats for the last 180 days into Postgres.
This script is intended for one-time use after migration to Postgres.
"""
import asyncio
from backend.services.scraper_stats import PlayerStatsScraper, ESPNClient

async def main():
    print("Starting EPL backfill for last 180 days (bypassing last scrape date)...")
    async with PlayerStatsScraper.context(ESPNClient()) as stats_scraper:
        stats_scraper.SPORTS_CONFIG = [("soccer", "eng.1", "EPL")]
        from backend.db import get_session
        async with get_session() as session:
            # Always fetch all EPL game IDs for the last 180 days
            game_ids = await stats_scraper._get_recent_game_ids(session, "soccer", "eng.1", 180)
            print(f"Found {len(game_ids)} EPL games to backfill.")
            total_stats = 0
            from sqlalchemy import select
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from backend.models.games_results import GameResult
            from backend.models.game import Game
            for idx, game_id in enumerate(game_ids):
                print(f"[{idx+1}/{len(game_ids)}] Scraping EPL game {game_id}...")
                # 1. Ensure games and games_results row exist (minimal upsert if missing)
                try:
                    # Ensure games row exists (all columns, including moved_at)
                    game_row = await session.execute(select(Game).where(Game.game_id == game_id))
                    game_exists = game_row.scalar_one_or_none()
                    if not game_exists:
                        await session.execute(
                            pg_insert(Game).values(
                                game_id=game_id,
                                sport="EPL",
                                league="eng.1",
                                sport_id=None,
                                home_team_id=None,
                                away_team_id=None,
                                home_team_name=None,
                                away_team_name=None,
                                home_score=None,
                                away_score=None,
                                period=None,
                                clock=None,
                                start_time=None,
                                status=None,
                                venue=None,
                                score=None,
                                lines_json=None,
                                odds_history_json=None,
                                play_by_play_json=None,
                                boxscore_json=None,
                                head_to_head_json=None
                            ).on_conflict_do_nothing()
                        )
                        await session.commit()
                    # Ensure games_results row exists (only valid columns)
                    result_row = await session.execute(select(GameResult).where(GameResult.game_id == game_id))
                    result_exists = result_row.scalar_one_or_none()
                    if not result_exists:
                        await session.execute(
                            pg_insert(GameResult).values(
                                game_id=game_id,
                                sport="EPL",
                                league="eng.1",
                                season=None,
                                season_type=None,
                                week=None,
                                round=None,
                                start_time=None,
                                end_time=None,
                                venue=None,
                                home_team_id=None,
                                away_team_id=None,
                                home_team_name=None,
                                away_team_name=None,
                                home_logo=None,
                                away_logo=None,
                                home_score=None,
                                away_score=None,
                                status=None,
                                attendance=None,
                                referees=None,
                                weather=None,
                                moved_at=None
                            ).on_conflict_do_nothing()
                        )
                        await session.commit()
                except Exception as e:
                    print(f"[Upsert] Error for game {game_id}: {e}")
                    await session.rollback()
                # 2. Scrape and save player stats for this game
                try:
                    # Patch: Always re-check and upsert games_results before player stats
                    result_row = await session.execute(select(GameResult).where(GameResult.game_id == game_id))
                    result_exists = result_row.scalar_one_or_none()
                    if not result_exists:
                        await session.execute(
                            pg_insert(GameResult).values(
                                game_id=game_id,
                                sport="EPL",
                                league="eng.1",
                                home_score=None,
                                away_score=None,
                                status=None,
                                attendance=None,
                                referees=None,
                                weather=None,
                            ).on_conflict_do_nothing()
                        )
                        await session.commit()
                    stats_count = await stats_scraper._scrape_game_boxscore(
                        session, game_id, "soccer", "eng.1", "EPL"
                    )
                    print(f"[Boxscore] Saved {stats_count} player stats for game {game_id}")
                    total_stats += stats_count
                    await session.commit()
                except Exception as e:
                    print(f"[Boxscore] Error for game {game_id}: {e}")
                    await session.rollback()
            print(f"EPL backfill complete: {total_stats} player stat records added.")

if __name__ == "__main__":
    asyncio.run(main())
