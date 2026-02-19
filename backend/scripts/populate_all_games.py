"""
Script to ensure both fresh (upcoming/live) and completed (results) games are always populated.
"""
import asyncio
from backend.db import get_session
from backend.services.aai.fresh_data_scraper import FreshDataScraper
from backend.services.scraper_stats import PlayerStatsScraper, ESPNClient

async def main():
    async with get_session() as session:
        print("[1/2] Scraping all fresh data (upcoming/live games, injuries, weather)...")
        fresh_scraper = FreshDataScraper(session)
        await fresh_scraper.scrape_all_fresh_data()
        print("[2/2] Scraping all completed games (results/stats)...")
        stats_scraper = PlayerStatsScraper(ESPNClient())
        await stats_scraper.scrape_recent_games(days_back=7)
        print("✅ All fresh and completed games populated.")

if __name__ == "__main__":
    asyncio.run(main())
