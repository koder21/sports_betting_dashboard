from backend.models.games_results import GameResult
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
from backend.db import get_session
from backend.services.espn_client import ESPNClient
from backend.services.scraper_stats import PlayerStatsScraper

async def main():
    game_id = "401810631"
    sport_type = "basketball"
    league = "nba"
    sport_name = "NBA"
    async with get_session() as session:
        client = ESPNClient()
        scraper = PlayerStatsScraper(client, session)
        # Upsert minimal row into games_results if missing
        await session.execute(
            pg_insert(GameResult).values(
                game_id=game_id,
                sport=sport_name,
                league=league,
                start_time=None,
                home_team_id=None,
                away_team_id=None,
                home_team_name=None,
                away_team_name=None,
                status=None,
            ).on_conflict_do_nothing(index_elements=['game_id'])
        )
        stats_count = await scraper._scrape_game_boxscore(session, game_id, sport_type, league, sport_name)
        print(f"Scraped {stats_count} player stats for game {game_id}")
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
