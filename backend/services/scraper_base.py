from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .espn_client import ESPNClient


class ScraperBase(ABC):
    def __init__(self, client: ESPNClient) -> None:
        self.client = client

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        raise NotImplementedError