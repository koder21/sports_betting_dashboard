"""
Enhanced DraftKings scraper with maximum anti-bot evasion.

Techniques:
- Full browser headers with all modern fields
- Request delays to avoid detection
- Connection pooling/persistence
- Realistic browser session simulation
"""
import asyncio
import aiohttp
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class BrowserLikeDKScraper:
    """DraftKings scraper mimicking real browser behavior"""
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=15)
    
    async def __aenter__(self):
        # Connector with persistent connection
        connector = aiohttp.TCPConnector(
            ssl=True,
            limit_per_host=1,  # Slow down requests
            ttl_dns_cache=300,
        )
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_full_headers(self) -> Dict[str, str]:
        """Complete browser headers - all fields a real Chrome browser sends"""
        return {
            "Host": "www.draftkings.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    
    async def scrape_all_sources(self, sport: str, date: str = None) -> Dict[str, Any]:
        """Try DraftKings with heavy browser simulation"""
        errors = []
        
        try:
            logger.info(f"Attempting DraftKings (enhanced) for {sport}")
            
            # Simulate "thinking time" before request (like a real user)
            await asyncio.sleep(random.uniform(1, 3))
            
            props = await self.scrape_draftkings(sport, date)
            
            if props and len(props) > 0:
                logger.info(f"✅ Successfully scraped {len(props)} props from DraftKings")
                return {
                    "props": props,
                    "source": "draftkings",
                    "errors": errors,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                errors.append("draftkings: No props found (possible bot detection)")
                logger.warning("DraftKings returned no props")
        
        except Exception as e:
            error_msg = f"draftkings: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
        
        logger.error(f"DraftKings failed for {sport}: {errors}")
        return {
            "props": [],
            "source": "none",
            "errors": errors,
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def scrape_draftkings(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """Scrape DraftKings with full browser simulation"""
        try:
            sport_id = self._get_dk_sport_id(sport)
            if not sport_id:
                logger.error(f"Unsupported sport: {sport}")
                return []
            
            # The actual API endpoint
            url = f"https://www.draftkings.com/api/sportscontent/v2/sports/{sport_id}/offerings"
            
            headers = self._get_full_headers()
            
            logger.info(f"Requesting: {url}")
            logger.info(f"Headers: User-Agent={headers['User-Agent'][:50]}...")
            
            # Make request with full browser headers
            async with self.session.get(url, headers=headers, ssl=True) as response:
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status == 403:
                    logger.error(f"🚫 Blocked (403) - Akamai WAF detection")
                    return []
                elif response.status == 404:
                    logger.error(f"Not found (404)")
                    return []
                elif response.status != 200:
                    logger.error(f"Error {response.status}: {await response.text()}")
                    return []
                
                data = await response.json()
                logger.info(f"Received JSON response with keys: {list(data.keys())}")
                
                props = self._parse_response(data, sport)
                return props
        
        except asyncio.TimeoutError:
            logger.error("Request timeout (15s)")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_dk_sport_id(self, sport: str) -> Optional[int]:
        """Map sport to DraftKings sport ID"""
        sport_map = {
            "NBA": 4,
            "NFL": 1,
            "MLB": 5,
            "NHL": 6,
        }
        return sport_map.get(sport.upper())
    
    def _parse_response(self, data: dict, sport: str) -> List[Dict[str, Any]]:
        """Parse DraftKings response"""
        props = []
        try:
            # Try to extract offerings
            if "offering" in data:
                offering = data["offering"]
                sub_contests = offering.get("subContests", [])
                
                logger.info(f"Found {len(sub_contests)} sub-contests")
                
                for sub_contest in sub_contests:
                    games = sub_contest.get("games", [])
                    for game in games:
                        contenders = game.get("contenders", [])
                        for contender in contenders:
                            player_name = contender.get("displayName", "")
                            contests = contender.get("contests", [])
                            
                            for contest in contests:
                                outcomes = contest.get("outcomes", [])
                                
                                # Extract over/under
                                for outcome in outcomes:
                                    if outcome.get("oddsAmerican"):
                                        prop_dict = {
                                            "player_name": player_name,
                                            "sport": sport,
                                            "sportsbook": "DraftKings",
                                            "scraped_at": datetime.now(timezone.utc).isoformat()
                                        }
                                        props.append(prop_dict)
            
            logger.info(f"Parsed {len(props)} props from response")
            return props
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return []


async def test_enhanced_scraper():
    """Test the enhanced scraper"""
    async with BrowserLikeDKScraper() as scraper:
        result = await scraper.scrape_all_sources("NBA")
        return result


if __name__ == "__main__":
    result = asyncio.run(test_enhanced_scraper())
    print(f"\n🔍 Result: {result}")
