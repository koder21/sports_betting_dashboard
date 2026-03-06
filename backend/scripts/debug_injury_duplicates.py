# Debug script to print duplicate injuries by (player_id, team_id, description)
from collections import Counter
from backend.services.aai.fresh_data_scraper import FreshDataScraper
import asyncio
import logging
import os

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql+asyncpg://postgres:postgres@localhost:5432/sports_intel"

async def main() -> None:
    """
    Prints duplicate injuries by (player_id, team_id, description).
    Fetches injury data from ESPN and counts duplicates.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[call-overload]
    async with async_session() as session:
        scraper = FreshDataScraper(session)
        # Only fetch injuries, don't upsert
        all_injuries = []
        async def collect_injuries():
            # Use the same INJURY_SPORTS as in fresh_data_scraper
            INJURY_SPORTS = [
                ("basketball", "nba",                    "NBA"),
                ("football",   "nfl",                    "NFL"),
                ("hockey",     "nhl",                    "NHL"),
                ("basketball", "mens-college-basketball", "NCAAB"),
                ("football",   "college-football",        "NCAAF"),
                ("baseball",   "mlb",                    "MLB"),
            ]
            async def fetch(sport_type, league, label):
                url = (f"https://site.api.espn.com/apis/site/v2/sports"
                       f"/{sport_type}/{league}/injuries")
                data = await scraper.espn_client.get_json(url)
                injuries = []
                for team_block in data.get("injuries", []):
                    team_info = team_block.get("team", {})
                    team_id   = str(team_info.get("id", ""))
                    for inj in team_block.get("injuries", []):
                        athlete  = inj.get("athlete", {})
                        injuries.append({
                            "player_id":   str(athlete.get("id", "")),
                            "team_id":     team_id,
                            "description": inj.get("longComment", inj.get("shortComment", "")),
                        })
                return injuries
            tasks = [fetch(st, lg, label) for st, lg, label in INJURY_SPORTS]
            results = await asyncio.gather(*tasks)
            for sub in results:
                all_injuries.extend(sub)
        await collect_injuries()
        # Count duplicates by (player_id, team_id, description)
        keys = [(i["player_id"], i["team_id"], i["description"]) for i in all_injuries]
        counter = Counter(keys)
        dups = [k for k, v in counter.items() if v > 1]
        logging.info(f"Total injuries: {len(all_injuries)}")
        logging.info(f"Duplicate (player_id, team_id, description) keys: {len(dups)}")
        if dups:
            logging.info("Sample duplicates:")
            for k in dups[:10]:
                logging.info(str(k))
    await engine.dispose()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
