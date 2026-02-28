import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.services.aai.fresh_data_scraper import FreshDataScraper
import os

# Adjust these as needed for your environment
DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql+asyncpg://postgres:postgres@localhost:5432/sports_intel"

async def main() -> None:
    """
    Scrapes injuries from ESPN and upserts them into the database.
    Prints the total number of injuries upserted.
    """
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        scraper = FreshDataScraper(session)
        count = await scraper._scrape_injuries()
        logging.info(f"[InjuryScrape] FINAL: {count} injuries upserted.")
    await engine.dispose()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
