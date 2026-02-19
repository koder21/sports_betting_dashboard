"""ESPN API client for fetching sports data."""
import asyncio
import aiohttp
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone


class ESPNClient:
    """Async client for ESPN API endpoints."""
    
    BASE = "https://site.web.api.espn.com/apis/v2/sports"
    
    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def get_json(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Fetch JSON from ESPN API with graceful error handling.
        
        Args:
            url: API endpoint URL
            timeout: Request timeout in seconds
            
        Returns:
            JSON response dict or None on error
        """
        session = await self._get_session()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except asyncio.TimeoutError:
            # Timeout expected for some slow endpoints
            return None
        except Exception:
            # Other errors: return None gracefully for resilience
            return None
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as e:
                # Log but don't fail on cleanup errors
                # FIX: Corrected typo from "ESP NClient" to "ESPNClient"
                print(f"Error closing ESPNClient session: {e}")
    
    async def get_json_with_fallback(
        self,
        primary_url: str,
        fallback_url: str,
        timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Try primary URL, fall back to fallback URL on failure.
        
        Args:
            primary_url: First URL to try
            fallback_url: Backup URL if primary fails
            timeout: Request timeout in seconds
            
        Returns:
            JSON response or None if both fail
        """
        result = await self.get_json(primary_url, timeout)
        if result is not None:
            return result
        return await self.get_json(fallback_url, timeout)
    
    def date_range_params(self, days_back: int = 1, days_forward: int = 1) -> tuple[str, str]:
        """
        Return date range for ESPN scoreboard API queries.
        
        Args:
            days_back: Days before today to include
            days_forward: Days after today to include
            
        Returns:
            (start_date, end_date) in YYYYMMDD format
        """
        now = datetime.utcnow()
        start = (now - timedelta(days=days_back)).strftime("%Y%m%d")
        end = (now + timedelta(days=days_forward)).strftime("%Y%m%d")
        return start, end
    
    def parse_date(self, date_str: str) -> datetime:
        """
        Parse ESPN date strings into UTC datetime objects.
        
        Supports ISO format (fastest), falls back to dateutil for other formats.
        
        Args:
            date_str: Date string from ESPN API
            
        Returns:
            UTC datetime object
        """
        try:
            # ESPN often uses ISO format with trailing Z (fastest path)
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except ValueError:
            try:
                # Fallback to dateutil for non-standard formats
                from dateutil import parser as date_parser
                dt = date_parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                # Last resort: return current UTC time
                return datetime.utcnow().replace(tzinfo=timezone.utc)
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure session is closed."""
        await self.close()


# Sport configuration for easy reference
SPORT_CONFIG: Dict[str, Dict[str, Any]] = {
    "nba": {"path": "/basketball/nba", "cdn": "nba"},
    "nfl": {"path": "/football/nfl", "cdn": "nfl"},
    "nhl": {"path": "/hockey/nhl", "cdn": "nhl"},
    "mlb": {"path": "/baseball/mlb", "cdn": "mlb"},
    "ncaaf": {"path": "/football/college-football", "cdn": "college-football"},
    "ncaab": {"path": "/basketball/mens-college-basketball", "cdn": "mens-college-basketball"},
    "soccer": {"path": "/soccer", "cdn": None, "leagues": ["eng.1"]},
}