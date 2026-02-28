"""
Script to ensure both fresh (upcoming/live) and completed (results) games are always populated.
"""
import asyncio
import logging
from backend.db import get_session
from backend.services.aai.fresh_data_scraper import FreshDataScraper
from backend.services.scraper_stats import PlayerStatsScraper, ESPNClient

async def main() -> None:
    """
    Ensures both fresh (upcoming/live) and completed (results) games are always populated.
    Scrapes fresh data and recent completed games.
    """
    async with get_session() as session:
        logging.info("[1/2] Scraping all fresh data (upcoming/live games, injuries, weather)...")
        fresh_scraper = FreshDataScraper(session)
        await fresh_scraper.scrape_all_fresh_data()
        logging.info("[2/2] Scraping all completed games (results/stats)...")
        stats_scraper = PlayerStatsScraper(ESPNClient())
        await stats_scraper.scrape_recent_games(days_back=7)
        logging.info("✅ All fresh and completed games populated.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
