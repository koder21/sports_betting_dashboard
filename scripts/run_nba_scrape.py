import asyncio
import sys
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


async def main():
    from backend.db import AsyncSessionLocal
    from backend.services.espn_client import ESPNClient
    from backend.services.scraping import NBAScraper
    from sqlalchemy import text

    client = ESPNClient()
    async with AsyncSessionLocal() as session:
        scraper = NBAScraper(session, client)
        print('Running NBA scraper...')
        try:
            await scraper.scrape()
            await session.commit()
            print('Scrape complete and committed.')
        except Exception as e:
            print('Scraper error:', e)
        # Show counts
        for tbl in ('games_upcoming','games_live','games_results'):
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                cnt = res.scalar_one()
                print(f"{tbl}: {cnt} rows")
            except Exception as ex:
                print(f"{tbl}: error -", ex)
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
