from .base import BaseScraper
from .common_team_league import TeamLeagueScraper

class MLBScraper(BaseScraper):
    async def scrape(self) -> None:
        scraper = TeamLeagueScraper(self.session, self.client, "mlb", None)
        await scraper.scrape()
