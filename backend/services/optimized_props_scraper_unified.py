import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class PropsScraperUnified:    
    # DraftKings sport IDs
    DK_SPORT_IDS = {
        "NBA": 4,
        "NFL": 1,
        "MLB": 5,
        "NHL": 6,
        "MLS": 10,
        "NCAAB": 24,
        "NCAAF": 25,
    }
    
    # ESPN sport paths
    ESPN_SPORT_PATHS = {
        "NBA": "nba",
        "NFL": "nfl",
        "MLB": "mlb",
        "NHL": "nhl",
        "NCAAB": "college-basketball",
        "NCAAF": "college-football",
        "Soccer": "soccer"
    }
    
    def __init__(self, timeout: int = 15):
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=True, limit_per_host=1)
        self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_props(
        self,
        sport: str,
        sources: Optional[List[str]] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape player props from available sources.
        
        Args:
            sport: "NBA", "NFL", "MLB", "NHL", etc.
            sources: List of sources to try (["draftkings", "espn"])
            date: Optional date filter (YYYY-MM-DD)
            
        Returns:
            {
                "props": [...],
                "source": "draftkings" | "espn" | "none",
                "errors": [],
                "success": bool,
                "timestamp": ISO timestamp
            }
        """
        if sources is None:
            sources = ["draftkings", "espn"]
        
        errors: List[Any] = []
        
        # Try each source in priority order
        for source in sources:
            try:
                logger.info(f"Attempting {source} for {sport}")
                
                if source == "draftkings":
                    props = await self._scrape_draftkings(sport, date)
                elif source == "espn":
                    props = await self._scrape_espn(sport)
                else:
                    continue
                
                if props and len(props) > 0:
                    logger.info(f"✓ {len(props)} props from {source}")
                    return {
                        "props": props,
                        "source": source,
                        "errors": errors,
                        "success": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    errors.append(f"{source}: No props found")
            
            except Exception as e:
                error_msg = f"{source}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        # All sources failed
        logger.error(f"All sources failed for {sport}: {errors}")
        return {
            "props": [],
            "source": "none",
            "errors": errors,
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _scrape_draftkings(self, sport: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape DraftKings API for player props.
        
        Note: DraftKings often blocks automated requests with 403 Forbidden.
        This is a best-effort implementation.
        """
        sport_id = self.DK_SPORT_IDS.get(sport.upper())
        if not sport_id:
            logger.error(f"Unsupported sport for DraftKings: {sport}")
            return []
        
        url = f"https://www.draftkings.com/api/sportscontent/v2/sports/{sport_id}/offerings"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        
        try:
            if not self.session:
                connector = aiohttp.TCPConnector(ssl=True, limit_per_host=1)
                self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)
            async with self.session.get(url, headers=headers) as response:
                if response.status == 403:
                    logger.warning("DraftKings blocked request (403 Forbidden)")
                    return []
                elif response.status != 200:
                    logger.warning(f"DraftKings returned {response.status}")
                    return []
                
                data = await response.json()
                return self._parse_draftkings_response(data, sport)
        
        except asyncio.TimeoutError:
            logger.error("DraftKings request timeout")
            return []
        except Exception as e:
            logger.error(f"DraftKings error: {e}")
            return []
    
    def _parse_draftkings_response(self, data: dict, sport: str) -> List[Dict[str, Any]]:
        """Parse DraftKings API response into standardized props."""
        props = []
        
        try:
            offering = data.get("offering", {})
            sub_contests = offering.get("subContests", [])
            
            for sub_contest in sub_contests:
                games = sub_contest.get("games", [])
                
                for game in games:
                    contenders = game.get("contenders", [])
                    
                    for contender in contenders:
                        player_name = contender.get("displayName", "")
                        contests = contender.get("contests", [])
                        
                        for contest in contests:
                            outcomes = contest.get("outcomes", [])
                            
                            # Extract over/under from outcomes
                            over_odds = None
                            under_odds = None
                            line = None
                            
                            for outcome in outcomes:
                                outcome_name = outcome.get("displayName", "").lower()
                                odds_american = outcome.get("oddsAmerican", 0)
                                line_value = outcome.get("line")
                                
                                decimal_odds = self._american_to_decimal(odds_american)
                                
                                if "over" in outcome_name:
                                    over_odds = decimal_odds
                                    line = line_value
                                elif "under" in outcome_name:
                                    under_odds = decimal_odds
                                    line = line_value
                            
                            # Only add if we have both over and under
                            if over_odds and under_odds and line:
                                prop_type = self._extract_prop_type(contest.get("displayName", ""))
                                
                                props.append({
                                    "player_name": player_name,
                                    "prop_type": prop_type,
                                    "over_odds": over_odds,
                                    "under_odds": under_odds,
                                    "line": line,
                                    "sportsbook": "DraftKings",
                                    "sport": sport,
                                    "scraped_at": datetime.now(timezone.utc).isoformat()
                                })
        
        except Exception as e:
            logger.error(f"DraftKings parse error: {e}")
        
        return props
    
    async def _scrape_espn(self, sport: str) -> List[Dict[str, Any]]:
        """
        Scrape ESPN for player props (limited coverage).
        
        Note: ESPN has very limited prop coverage and no public API.
        This is a fallback only.
        """
        sport_path = self.ESPN_SPORT_PATHS.get(sport.upper())
        if not sport_path:
            logger.error(f"Unsupported sport for ESPN: {sport}")
            return []
        
        # ESPN props are difficult to scrape without JavaScript rendering
        # For now, return empty - can be enhanced later with Selenium/Playwright
        logger.info("ESPN props not yet fully implemented (requires JS rendering)")
        return []
    
    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal odds."""
        try:
            american_odds = float(american_odds)
            if american_odds > 0:
                return (american_odds / 100) + 1
            else:
                return (100 / abs(american_odds)) + 1
        except:
            return 2.0  # Default fallback
    
    def _extract_prop_type(self, display_name: str) -> str:
        """Extract standardized prop type from display name."""
        name_lower = display_name.lower()
        
        # Map common terms to prop types
        if "point" in name_lower:
            return "Points"
        elif "assist" in name_lower:
            return "Assists"
        elif "rebound" in name_lower:
            return "Rebounds"
        elif "steal" in name_lower:
            return "Steals"
        elif "block" in name_lower:
            return "Blocks"
        elif "three" in name_lower or "3pt" in name_lower or "3-pt" in name_lower:
            return "3-Pointers"
        elif "touchdown" in name_lower or "td" in name_lower:
            return "Touchdowns"
        elif "rush" in name_lower and "yard" in name_lower:
            return "Rushing Yards"
        elif "pass" in name_lower and "yard" in name_lower:
            return "Passing Yards"
        elif "reception" in name_lower or "catch" in name_lower:
            return "Receptions"
        else:
            return display_name.strip()


async def scrape_daily_props(sports: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Scrape props for multiple sports.
    
    Args:
        sports: List of sports (["NBA", "NFL", etc.])
    
    Returns:
        Dict mapping sport to scrape results
    """
    results = {}
    
    async with PropsScraperUnified() as scraper:
        for sport in sports:
            logger.info(f"Scraping {sport}")
            result = await scraper.scrape_props(sport)
            results[sport] = result
            
            if result["success"]:
                logger.info(f"✓ {sport}: {len(result['props'])} props from {result['source']}")
            else:
                logger.warning(f"✗ {sport}: Failed - {result['errors']}")
    
    return results


# For backward compatibility
async def test_scraper():
    """Test the unified scraper."""
    async with PropsScraperUnified() as scraper:
        result = await scraper.scrape_props("NBA")
        return result


if __name__ == "__main__":
    result = asyncio.run(test_scraper())
    print(f"Result: {result}")