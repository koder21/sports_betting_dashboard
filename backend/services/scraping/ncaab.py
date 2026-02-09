from .base import BaseScraper
from .common_team_league import TeamLeagueScraper


class NCAABScraper(BaseScraper):
    async def scrape(self) -> None:
        scraper = TeamLeagueScraper(self.session, self.client, "ncaab", None)
        await scraper.scrape()