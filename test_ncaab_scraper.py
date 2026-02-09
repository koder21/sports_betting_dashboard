import asyncio
from backend.services.scraping.ncaab import NCAABScraper
from backend.db import AsyncSessionLocal, init_db
from backend.services.espn_client import ESPNClient

async def test():
    await init_db()
    async with AsyncSessionLocal() as session:
        client = ESPNClient()
        scraper = NCAABScraper(session, client)
        await scraper.scrape()
        await session.commit()
        print('✓ NCAAB scraper completed successfully!')
        await client.close()

asyncio.run(test())
