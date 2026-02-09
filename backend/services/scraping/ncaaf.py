from .base import BaseScraper
from ..espn_client import ESPNClient
from .common_team_league import TeamLeagueScraper


class NCAAFScraper(BaseScraper):
    async def scrape(self) -> None:
        scraper = TeamLeagueScraper(self.session, self.client, "ncaaf", None)
        await scraper.scrape()