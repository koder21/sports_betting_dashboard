"""
DraftKings Player Prop Scraper - Free API (no key required)

DraftKings provides a free, public API for props:
- No authentication required
- No rate limiting for normal use
- Reliable data structure
- Regular updates

Sources:
1. DraftKings API (primary) - Most reliable
2. ESPN data (fallback) - For context when DK unavailable
"""
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class DraftKingsPropScraper:
    """
    Scrape player props from DraftKings API (no authentication required).
    
    DraftKings provides a public API endpoint that returns:
    - Live games
    - Player props (points, rebounds, assists, etc.)
    - Odds for each prop
    - Updates in real-time
    """
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        # DraftKings API endpoints
        self.dk_api_base = "https://api.draftkings.com"
        self.dk_sportsbook = "https://www.draftkings.com/api/sportscontent/v2"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_dk_sport_id(self, sport: str) -> Optional[int]:
        """Map sport name to DraftKings sport ID"""
        sport_map = {
            "NBA": 4,
            "NFL": 1,
            "MLB": 5,
            "NHL": 6,
            "MLS": 10,
            "NCAAB": 24,
            "NCAAF": 25,
        }
        return sport_map.get(sport.upper())
    
    async def scrape_all_sources(self, sport: str, date: str = None) -> Dict[str, Any]:
        """
        Scrape props from DraftKings API with fallback to ESPN.
        
        Args:
            sport: "NBA", "NFL", "MLB", "NHL", etc.
            date: Optional date filter (YYYY-MM-DD)
        
        Returns:
            {
                "props": [...],
                "source": "draftkings",
                "errors": [],
                "success": True,
                "timestamp": ISO timestamp
            }
        """
        errors = []
        
        # Try DraftKings first (primary source)
        try:
            logger.info(f"Attempting DraftKings scrape for {sport}")
            props = await self.scrape_draftkings(sport, date)
            
            if props and len(props) > 0:
                logger.info(f"Successfully scraped {len(props)} props from DraftKings")
                return {
                    "props": props,
                    "source": "draftkings",
                    "errors": errors,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                errors.append("draftkings: No props found")
        except Exception as e:
            error_msg = f"draftkings: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
        
        # Fallback to ESPN
        try:
            logger.info(f"Falling back to ESPN for {sport}")
            props = await self.scrape_espn_props(sport)
            
            if props and len(props) > 0:
                logger.info(f"Successfully scraped {len(props)} props from ESPN")
                return {
                    "props": props,
                    "source": "espn",
                    "errors": errors,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                errors.append("espn: No props found")
        except Exception as e:
            error_msg = f"espn: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
        
        logger.error(f"All sources failed for {sport}: {errors}")
        return {
            "props": [],
            "source": "none",
            "errors": errors,
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def scrape_draftkings(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """
        Scrape player props from DraftKings API.
        
        The API structure returns offerings with subcontests for player props.
        """
        try:
            sport_id = self._get_dk_sport_id(sport)
            if not sport_id:
                logger.error(f"Unsupported sport: {sport}")
                return []
            
            # DraftKings API endpoint for sport offerings
            url = f"{self.dk_sportsbook}/sports/{sport_id}/offerings"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
            }
            
            logger.info(f"Fetching DraftKings API: {url}")
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"DraftKings returned {response.status}")
                    return []
                
                data = await response.json()
                props = self._parse_draftkings_response(data, sport)
                
                logger.info(f"Parsed {len(props)} props from DraftKings response")
                return props
        
        except Exception as e:
            logger.error(f"DraftKings scrape failed: {e}")
            return []
    
    def _parse_draftkings_response(self, data: dict, sport: str) -> List[Dict[str, Any]]:
        """
        Parse DraftKings API response structure.
        
        Response format:
        {
            "offering": {
                "id": 12345,
                "subContests": [
                    {
                        "id": "prop_id",
                        "displayName": "Player Points Over/Under",
                        "games": [
                            {
                                "id": "game_id",
                                "competitors": [...],
                                "contenders": [
                                    {
                                        "id": "contender_id",
                                        "displayName": "Player Name",
                                        "image": "...",
                                        "contests": [
                                            {
                                                "id": "contest_id",
                                                "displayName": "Over 24.5",
                                                "outcomes": [
                                                    {
                                                        "id": "outcome_id",
                                                        "line": 24.5,
                                                        "oddsAmerican": -110
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        """
        props = []
        
        try:
            offering = data.get("offering", {})
            sub_contests = offering.get("subContests", [])
            
            for sub_contest in sub_contests:
                contest_name = sub_contest.get("displayName", "")
                games = sub_contest.get("games", [])
                
                for game in games:
                    contenders = game.get("contenders", [])
                    
                    for contender in contenders:
                        player_name = contender.get("displayName", "")
                        contests = contender.get("contests", [])
                        
                        for contest in contests:
                            display_name = contest.get("displayName", "")
                            outcomes = contest.get("outcomes", [])
                            
                            # Extract over/under odds
                            over_odds = None
                            under_odds = None
                            line_value = None
                            
                            for outcome in outcomes:
                                outcome_name = outcome.get("displayName", "").lower()
                                odds_american = outcome.get("oddsAmerican", 0)
                                line = outcome.get("line")
                                
                                # Convert American odds to decimal
                                decimal_odds = self._american_to_decimal(odds_american)
                                
                                if "over" in outcome_name:
                                    over_odds = decimal_odds
                                    line_value = line
                                elif "under" in outcome_name:
                                    under_odds = decimal_odds
                                    line_value = line
                            
                            # Only add if we have both over and under odds
                            if over_odds and under_odds:
                                # Extract prop type from display name
                                prop_type = self._extract_prop_type(display_name, contest_name)
                                
                                prop = {
                                    "player_name": player_name,
                                    "prop_type": prop_type,
                                    "over_odds": over_odds,
                                    "under_odds": under_odds,
                                    "line": line_value,
                                    "sportsbook": "DraftKings",
                                    "sport": sport,
                                    "scraped_at": datetime.now(timezone.utc).isoformat()
                                }
                                props.append(prop)
            
            return props
        
        except Exception as e:
            logger.error(f"Error parsing DraftKings response: {e}")
            return []
    
    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal odds"""
        try:
            american_odds = float(american_odds)
            if american_odds > 0:
                return (american_odds / 100) + 1
            else:
                return (100 / abs(american_odds)) + 1
        except:
            return 2.0  # Default fallback
    
    def _extract_prop_type(self, display_name: str, contest_name: str) -> str:
        """Extract prop type from display name"""
        combined = f"{display_name} {contest_name}".lower()
        
        if "point" in combined:
            return "Points"
        elif "assist" in combined:
            return "Assists"
        elif "rebound" in combined:
            return "Rebounds"
        elif "steal" in combined:
            return "Steals"
        elif "block" in combined:
            return "Blocks"
        elif "three" in combined or "3pt" in combined:
            return "3-Pointers"
        elif "touchdown" in combined or "td" in combined:
            return "Touchdowns"
        elif "rush" in combined and "yard" in combined:
            return "Rushing Yards"
        elif "pass" in combined and "yard" in combined:
            return "Passing Yards"
        elif "reception" in combined or "catch" in combined:
            return "Receptions"
        else:
            return display_name.strip()
    
    async def scrape_espn_props(self, sport: str) -> List[Dict[str, Any]]:
        """
        Scrape basic props from ESPN as fallback.
        ESPN has less detailed prop data but is more reliable than sportsbook sites.
        """
        try:
            # For now, return empty - can be enhanced later
            # ESPN's props are more difficult to scrape without JavaScript rendering
            logger.info("ESPN fallback not yet implemented")
            return []
        except Exception as e:
            logger.error(f"ESPN scrape failed: {e}")
            return []


async def scrape_daily_props(sports: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Scrape props for multiple sports.
    
    Args:
        sports: List of sports (["NBA", "NFL", etc.])
    
    Returns:
        {
            "NBA": {
                "props": [...],
                "source": "draftkings",
                "success": True,
                ...
            },
            "NFL": {...}
        }
    """
    results = {}
    
    async with DraftKingsPropScraper() as scraper:
        for sport in sports:
            logger.info(f"Scraping {sport}")
            result = await scraper.scrape_all_sources(sport)
            results[sport] = result
            
            # Log results
            if result["success"]:
                logger.info(f"✅ {sport}: {len(result['props'])} props from {result['source']}")
            else:
                logger.warning(f"❌ {sport}: No props found. Errors: {result['errors']}")
    
    return results


if __name__ == "__main__":
    # Test the scraper
    result = asyncio.run(scrape_daily_props(["NBA"]))
    print(result)
