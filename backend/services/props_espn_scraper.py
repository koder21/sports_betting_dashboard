"""
ESPN Player Props Scraper

ESPN has player props available through their website and API.
This scraper attempts to extract them without authentication.
"""
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ESPNPropScraper:
    """Scrape player props from ESPN"""
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=10)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_all_sources(self, sport: str) -> Dict[str, Any]:
        """Try ESPN for player props"""
        errors = []
        
        try:
            logger.info(f"Attempting ESPN props for {sport}")
            props = await self.scrape_espn_props(sport)
            
            if props and len(props) > 0:
                logger.info(f"✅ Successfully scraped {len(props)} props from ESPN")
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
            logger.error(error_msg)
            errors.append(error_msg)
        
        logger.error(f"ESPN props failed: {errors}")
        return {
            "props": [],
            "source": "none",
            "errors": errors,
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def scrape_espn_props(self, sport: str) -> List[Dict[str, Any]]:
        """
        Scrape player props from ESPN.
        
        ESPN has props in their odds/betting section.
        """
        try:
            sport_key = self._get_espn_sport_key(sport)
            if not sport_key:
                logger.error(f"Unsupported sport: {sport}")
                return []
            
            # ESPN's odds/betting section with props
            url = f"https://www.espn.com/{sport_key}/odds/playerprops"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            }
            
            logger.info(f"Fetching ESPN props: {url}")
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"ESPN returned {response.status}")
                    return []
                
                html = await response.text()
                props = self._parse_espn_html(html, sport)
                
                logger.info(f"Parsed {len(props)} props from ESPN")
                return props
        
        except Exception as e:
            logger.error(f"ESPN scrape failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_espn_html(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """Parse ESPN player props HTML"""
        props = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for prop tables/sections
            # ESPN structures props in various containers
            
            # Try multiple selectors for prop cards
            selectors = [
                'div[class*="prop"]',
                'div[class*="PlayerProp"]',
                'div[data-testid*="prop"]',
                'tr[data-testid*="prop"]',
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
                
                if elements:
                    for elem in elements:
                        prop = self._extract_prop_from_element(elem, sport)
                        if prop:
                            props.append(prop)
            
            return props
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return []
    
    def _extract_prop_from_element(self, elem, sport: str) -> Optional[Dict[str, Any]]:
        """Try to extract prop data from HTML element"""
        try:
            # Look for player name
            player_text = elem.get_text(strip=True)
            
            if not player_text or len(player_text) < 3:
                return None
            
            # Look for odds in element
            odds_elements = elem.find_all(['span', 'div'], class_=lambda x: x and ('odd' in x.lower() or 'price' in x.lower()))
            
            if not odds_elements or len(odds_elements) < 2:
                return None
            
            # Try to extract numbers (odds)
            odds_text = ' '.join([e.get_text(strip=True) for e in odds_elements])
            
            # Very basic prop if we found anything
            if odds_text:
                return {
                    "player_name": player_text[:50],  # Truncate long text
                    "prop_type": "Unknown",
                    "sportsbook": "ESPN",
                    "sport": sport,
                    "raw_data": odds_text,
                    "scraped_at": datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            logger.debug(f"Element parse error: {e}")
        
        return None
    
    def _get_espn_sport_key(self, sport: str) -> Optional[str]:
        """Map sport to ESPN URL key"""
        sport_map = {
            "NBA": "nba",
            "NFL": "nfl",
            "MLB": "mlb",
            "NHL": "nhl",
            "NCAAB": "college-basketball",
            "NCAAF": "college-football",
        }
        return sport_map.get(sport.upper())


async def test_espn_props():
    """Test ESPN props scraper"""
    async with ESPNPropScraper() as scraper:
        result = await scraper.scrape_all_sources("NBA")
        return result


if __name__ == "__main__":
    result = asyncio.run(test_espn_props())
    print(f"Result: {result}")
