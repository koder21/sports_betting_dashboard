import asyncio
import sys
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.db import AsyncSessionLocal
from backend.services.espn_client import ESPNClient
from backend.services.scraping import (
    NBAScraper,
    NFLScraper,
    NHLScraper,
    NCAABScraper,
    NCAAFScraper,
    SoccerScraper,
    UFCScraper,
)
from sqlalchemy import text

SCRAPERS = [
    ("NBA", NBAScraper),
    ("NFL", NFLScraper),
    ("NHL", NHLScraper),
    ("NCAAB", NCAABScraper),
    ("NCAAF", NCAAFScraper),
    ("SOCCER", SoccerScraper),
    ("UFC", UFCScraper),
]

async def run_all():
    client = ESPNClient()
    async with AsyncSessionLocal() as session:
        for name, ScraperCls in SCRAPERS:
            print(f"Running {name} scraper...")
            scraper = ScraperCls(session, client)
            try:
                await scraper.scrape()
                await session.commit()
                print(f"{name} scrape completed and committed.")
            except Exception as e:
                print(f"{name} scraper error:", e)
        print("\nTable counts:")
        for tbl in ('teams','players','games','games_upcoming','games_live','games_results'):
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                cnt = res.scalar_one()
                print(f"{tbl}: {cnt}")
            except Exception as ex:
                print(f"{tbl}: error -", ex)
    await client.close()

if __name__ == '__main__':
    asyncio.run(run_all())
