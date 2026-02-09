import asyncio
from sqlalchemy import text, delete
from backend.db import AsyncSessionLocal
from backend.models.player_stats import PlayerStats
from backend.services.scraper_stats import PlayerStatsScraper
from backend.services.espn_client import ESPNClient

async def main():
    client = ESPNClient()
    try:
        async with AsyncSessionLocal() as session:
            # Delete only NFL player stats
            print("Deleting existing NFL player stats...")
            result = await session.execute(
                delete(PlayerStats).where(PlayerStats.sport == "NFL")
            )
            await session.commit()
            print(f"Deleted {result.rowcount} NFL stat records")
            
            # Re-scrape NFL stats from last 180 days
            print("\nRe-scraping NFL stats...")
            await session.execute(text("PRAGMA busy_timeout=60000"))
            scraper = PlayerStatsScraper(client, session)
            await scraper.scrape_recent_games(days_back=180)
            print("NFL stats re-scrape complete!")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
