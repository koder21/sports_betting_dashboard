from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseScraper
from ..espn_client import ESPNClient
from .common_team_league import TeamLeagueScraper


class NBAScraper(BaseScraper):
    async def scrape(self) -> None:
        scraper = TeamLeagueScraper(self.session, self.client, "nba", None)
        await scraper.scrape()