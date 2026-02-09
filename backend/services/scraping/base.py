from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from ..espn_client import ESPNClient


class BaseScraper(ABC):
    def __init__(self, session: AsyncSession, client: ESPNClient):
        self.session = session
        self.client = client

    @abstractmethod
    async def scrape(self) -> None:
        ...