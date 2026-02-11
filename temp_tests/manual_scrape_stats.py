#!/usr/bin/env python3
"""
Manual script to scrape player stats for recent games.
Useful for debugging and backfilling missing stats.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.services.espn_client import ESPNClient
from backend.services.scraper_stats import PlayerStatsScraper


async def main():
    # Create database session
    engine = create_async_engine("sqlite+aiosqlite:///sports_intel.db")
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
    
    client = ESPNClient()
    
    try:
        async with SessionFactory() as session:
            scraper = PlayerStatsScraper(client, session)
            
            print("Starting player stats scrape for last 7 days...")
            await scraper.scrape_recent_games(days_back=7)
            print("Scrape completed successfully!")
            
    except Exception as e:
        print(f"Error during scrape: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
