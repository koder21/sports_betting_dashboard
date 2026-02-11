import aiohttp
import asyncio
from typing import Any, Dict, Optional
from functools import lru_cache
from datetime import datetime, timedelta, timezone

BASE_SITE = "https://site.api.espn.com/apis/site/v2/sports"
BASE_CORE = "https://site.web.api.espn.com/apis/v2/sports"
BASE_CDN = "https://cdn.espn.com/core"

SPORT_CONFIG: Dict[str, Dict[str, Any]] = {
    "nba": {"path": "/basketball/nba", "cdn": "nba", "leagues": None},
    "nfl": {"path": "/football/nfl", "cdn": "nfl", "leagues": None},
    "nhl": {"path": "/hockey/nhl", "cdn": "nhl", "leagues": None},
    "mlb": {"path": "/baseball/mlb", "cdn": "mlb", "leagues": None},
    "ufc": {"path": "/mma/ufc", "cdn": "ufc", "leagues": None},
    "ncaaf": {"path": "/football/college-football", "cdn": "college-football", "leagues": None},
    "ncaab": {"path": "/basketball/mens-college-basketball", "cdn": "mens-college-basketball", "leagues": None},
    "wnba": {"path": "/basketball/wnba", "cdn": "wnba", "leagues": None},
    "soccer": {"path": "/soccer", "cdn": None, "leagues": ["eng.1"]},
}

class ESPNClient:
    BASE = "https://site.web.api.espn.com/apis/v2/sports"

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    # removed @lru_cache (not compatible with async functions)
    async def get_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON from ESPN API with graceful error handling"""
        session = await self._get_session()
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except asyncio.TimeoutError:
            # Timeout is expected for some slow endpoints
            return None
        except Exception:
            # Other errors: return None gracefully for resilience
            return None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            try:
                # Wait a bit for any pending requests to complete
                await asyncio.sleep(0.1)
                await self._session.close()
            except Exception as e:
                # Log but don't fail on cleanup errors
                print(f"Error closing ESP NClient session: {e}")

    async def get_json_with_fallback(self, primary_url: str, fallback_url: str) -> Optional[Dict[str, Any]]:
        """Try primary URL, fall back to fallback URL on failure."""
        result = await self.get_json(primary_url)
        if result is not None:
            return result
        return await self.get_json(fallback_url)

    def date_range_params(self, days_back: int = 1, days_forward: int = 1) -> tuple[str, str]:
        """Return date range for ESPN scoreboard API queries in YYYYMMDD format"""
        now = datetime.utcnow()
        start = (now - timedelta(days=days_back)).strftime("%Y%m%d")
        end = (now + timedelta(days=days_forward)).strftime("%Y%m%d")
        return start, end

    def parse_date(self, date_str: str) -> datetime:
        """Parse ESPN date strings into UTC datetime objects.
        
        Supports ISO format (fastest), falls back to dateutil for other formats.
        """
        try:
            # ESPN often uses ISO format with trailing Z (fastest path)
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except ValueError:
            try:
                # Fallback to dateutil for non-standard formats
                from dateutil import parser as _parser
                dt = _parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                # Last resort: return current UTC time
                return datetime.utcnow().replace(tzinfo=timezone.utc)