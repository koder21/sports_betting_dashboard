"""Test player scraping manually"""
import asyncio
from backend.db import AsyncSessionLocal
from backend.services.scraper_stats import PlayerStatsScraper
from backend.services.espn_client import ESPNClient

async def main():
    async with AsyncSessionLocal() as session:
        client = ESPNClient()
        scraper = PlayerStatsScraper(client, session)
        
        print("Starting roster scrape...")
        await scraper.scrape_teams_and_rosters()
        
        print("\nStarting game stats scrape...")
        await scraper.scrape_recent_games(days_back=3)
        
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
