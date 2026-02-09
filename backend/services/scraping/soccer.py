from .base import BaseScraper
from ..espn_client import ESPNClient, SPORT_CONFIG
from .common_team_league import TeamLeagueScraper
from sqlalchemy.ext.asyncio import AsyncSession


class SoccerScraper(BaseScraper):
    async def scrape(self) -> None:
        config = SPORT_CONFIG["soccer"]
        leagues = config["leagues"] or []
        for league in leagues:
            scraper = TeamLeagueScraper(self.session, self.client, "soccer", league)
            await scraper.scrape()