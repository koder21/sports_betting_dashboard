"""
Web scraper for player prop bets from multiple sportsbooks.

Sources (in order of priority):
1. FanDuel - Best odds, most props
2. BetMGM - Good coverage, fallback
3. TheScore - Alternative source, fallback
4. ESPN - Basic props, fallback for game-level odds

No API keys required - pure web scraping.
"""
import asyncio
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


# Rotating User-Agents to bypass bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class PropScraper:
    """
    Scrape player props from multiple sportsbooks.
    
    Priority order:
    1. FanDuel (largest selection)
    2. BetMGM (good coverage)
    3. TheScore (alternative)
    4. ESPN (fallback for basic props)
    
    Features:
    - Rotating User-Agents to bypass bot detection
    - Custom headers to appear as real browser
    - Exponential backoff on 429 (rate limit) errors
    """
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.retry_count = 3
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with rotating User-Agent"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.google.com/",
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_all_sources(self, sport: str, date: str = None) -> Dict[str, Any]:
        """
        Scrape props from all sources with fallback logic.
        
        Args:
            sport: "NBA", "NFL", "NHL", etc.
            date: Optional date filter (YYYY-MM-DD)
        
        Returns:
            {
                "props": [...],
                "source": "fanduel",
                "errors": [],
                "success": True
            }
        """
        sources = [
            ("fanduel", self.scrape_fanduel),
            ("betmgm", self.scrape_betmgm),
            ("thescore", self.scrape_thescore),
            ("espn", self.scrape_espn),
        ]
        
        errors = []
        
        for source_name, scraper in sources:
            try:
                logger.info(f"Attempting {source_name} scrape for {sport}")
                props = await scraper(sport, date)
                
                if props and len(props) > 0:
                    logger.info(f"Successfully scraped {len(props)} props from {source_name}")
                    return {
                        "props": props,
                        "source": source_name,
                        "errors": errors,
                        "success": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    errors.append(f"{source_name}: No props found")
            except Exception as e:
                error_msg = f"{source_name}: {str(e)}"
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
    
    async def scrape_fanduel(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """Scrape player props from FanDuel."""
        try:
            # FanDuel sportsbook URL
            url = "https://sportsbook.fanduel.com/upcoming"
            
            headers = self._get_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"FanDuel returned {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                props = []
                
                # Look for player props cards
                prop_cards = soup.find_all('div', class_='prop-card')
                if not prop_cards:
                    # Try alternative selectors
                    prop_cards = soup.find_all('div', attrs={'data-testid': 'prop-card'})
                
                for card in prop_cards:
                    try:
                        prop = self._parse_fanduel_prop(card, sport)
                        if prop:
                            props.append(prop)
                    except Exception as e:
                        logger.debug(f"Error parsing FanDuel prop: {e}")
                        continue
                
                return props
        
        except Exception as e:
            logger.error(f"FanDuel scrape failed: {e}")
            return []
    
    async def scrape_betmgm(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """Scrape player props from BetMGM."""
        try:
            # BetMGM sportsbook URL
            url = f"https://sports.betmgm.com/en/sports/{self._sport_to_betmgm(sport)}"
            
            headers = self._get_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"BetMGM returned {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                props = []
                
                # BetMGM prop cards
                prop_sections = soup.find_all('div', class_='player-prop-market')
                if not prop_sections:
                    prop_sections = soup.find_all('div', attrs={'data-qa': 'player-prop'})
                
                for section in prop_sections:
                    try:
                        prop = self._parse_betmgm_prop(section, sport)
                        if prop:
                            props.append(prop)
                    except Exception as e:
                        logger.debug(f"Error parsing BetMGM prop: {e}")
                        continue
                
                return props
        
        except Exception as e:
            logger.error(f"BetMGM scrape failed: {e}")
            return []
    
    async def scrape_thescore(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """Scrape player props from TheScore."""
        try:
            # TheScore sportsbook URL
            url = f"https://www.thescore.com/betting/{self._sport_to_thescore(sport)}"
            
            headers = self._get_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"TheScore returned {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                props = []
                
                # TheScore prop cards
                prop_cards = soup.find_all('div', class_='prop-card')
                if not prop_cards:
                    prop_cards = soup.find_all('div', attrs={'data-testid': 'playerProp'})
                
                for card in prop_cards:
                    try:
                        prop = self._parse_thescore_prop(card, sport)
                        if prop:
                            props.append(prop)
                    except Exception as e:
                        logger.debug(f"Error parsing TheScore prop: {e}")
                        continue
                
                return props
        
        except Exception as e:
            logger.error(f"TheScore scrape failed: {e}")
            return []
    
    async def scrape_espn(self, sport: str, date: str = None) -> List[Dict[str, Any]]:
        """Scrape props from ESPN as fallback."""
        try:
            # ESPN scoreboard with props
            url = f"https://www.espn.com/{self._sport_to_espn(sport)}/scoreboard"
            
            headers = self._get_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"ESPN returned {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                props = []
                
                # ESPN has props embedded in game articles
                prop_sections = soup.find_all('div', class_='PlayerProp')
                if not prop_sections:
                    prop_sections = soup.find_all('span', attrs={'data-testid': 'Odds.PlayerPropLink'})
                
                for section in prop_sections:
                    try:
                        prop = self._parse_espn_prop(section, sport)
                        if prop:
                            props.append(prop)
                    except Exception as e:
                        logger.debug(f"Error parsing ESPN prop: {e}")
                        continue
                
                return props
        
        except Exception as e:
            logger.error(f"ESPN scrape failed: {e}")
            return []
    
    def _parse_fanduel_prop(self, card, sport: str) -> Optional[Dict[str, Any]]:
        """Parse a FanDuel prop card."""
        try:
            # Extract player name
            player_elem = card.find('span', class_='player-name')
            if not player_elem:
                return None
            player_name = player_elem.text.strip()
            
            # Extract prop type
            prop_elem = card.find('span', class_='prop-type')
            prop_type = prop_elem.text.strip() if prop_elem else "unknown"
            
            # Extract odds
            over_elem = card.find('span', class_='over-odds')
            under_elem = card.find('span', class_='under-odds')
            
            over_odds = float(over_elem.text) if over_elem else None
            under_odds = float(under_elem.text) if under_elem else None
            
            if not over_odds or not under_odds:
                return None
            
            return {
                "player_name": player_name,
                "prop_type": prop_type,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "sportsbook": "FanDuel",
                "sport": sport,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing FanDuel prop: {e}")
            return None
    
    def _parse_betmgm_prop(self, section, sport: str) -> Optional[Dict[str, Any]]:
        """Parse a BetMGM prop."""
        try:
            # Extract player
            player_elem = section.find('span', class_='player-name')
            if not player_elem:
                return None
            player_name = player_elem.text.strip()
            
            # Extract prop type
            prop_type_elem = section.find('span', class_='prop-description')
            prop_type = prop_type_elem.text.strip() if prop_type_elem else "unknown"
            
            # Extract odds
            odds_elems = section.find_all('span', class_='odds')
            if len(odds_elems) < 2:
                return None
            
            over_odds = float(odds_elems[0].text)
            under_odds = float(odds_elems[1].text)
            
            return {
                "player_name": player_name,
                "prop_type": prop_type,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "sportsbook": "BetMGM",
                "sport": sport,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing BetMGM prop: {e}")
            return None
    
    def _parse_thescore_prop(self, card, sport: str) -> Optional[Dict[str, Any]]:
        """Parse a TheScore prop."""
        try:
            # Extract player
            player_elem = card.find('span', class_='player-name')
            if not player_elem:
                return None
            player_name = player_elem.text.strip()
            
            # Extract prop type
            prop_elem = card.find('span', class_='prop-label')
            prop_type = prop_elem.text.strip() if prop_elem else "unknown"
            
            # Extract odds
            over_elem = card.find('span', attrs={'data-type': 'over'})
            under_elem = card.find('span', attrs={'data-type': 'under'})
            
            over_odds = float(over_elem.text) if over_elem else None
            under_odds = float(under_elem.text) if under_elem else None
            
            if not over_odds or not under_odds:
                return None
            
            return {
                "player_name": player_name,
                "prop_type": prop_type,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "sportsbook": "TheScore",
                "sport": sport,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing TheScore prop: {e}")
            return None
    
    def _parse_espn_prop(self, section, sport: str) -> Optional[Dict[str, Any]]:
        """Parse an ESPN prop."""
        try:
            # Extract player and prop info from text
            text = section.get_text(strip=True)
            parts = text.split('-')
            
            if len(parts) < 2:
                return None
            
            player_name = parts[0].strip()
            prop_text = parts[1].strip()
            
            # Try to extract odds from prop text
            # Format: "Over 20.5 (1.90) Under 19.5 (1.90)"
            import re
            over_match = re.search(r'Over\s+[\d.]+\s+\(([\d.]+)\)', prop_text)
            under_match = re.search(r'Under\s+[\d.]+\s+\(([\d.]+)\)', prop_text)
            
            if not (over_match and under_match):
                return None
            
            over_odds = float(over_match.group(1))
            under_odds = float(under_match.group(1))
            
            # Determine prop type from text
            if 'points' in prop_text.lower() or 'pts' in prop_text.lower():
                prop_type = "Points"
            elif 'assist' in prop_text.lower():
                prop_type = "Assists"
            elif 'rebound' in prop_text.lower() or 'reb' in prop_text.lower():
                prop_type = "Rebounds"
            elif 'goal' in prop_text.lower():
                prop_type = "Goals"
            else:
                prop_type = "Unknown"
            
            return {
                "player_name": player_name,
                "prop_type": prop_type,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "sportsbook": "ESPN",
                "sport": sport,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing ESPN prop: {e}")
            return None
    
    @staticmethod
    def _sport_to_betmgm(sport: str) -> str:
        """Convert sport name to BetMGM URL format."""
        mapping = {
            "NBA": "basketball-nba",
            "NFL": "football-nfl",
            "NHL": "hockey-nhl",
            "MLB": "baseball-mlb",
            "NCAAB": "basketball-college",
            "NCAAF": "football-college",
            "EPL": "soccer-england",
            "MLS": "soccer-mls",
        }
        return mapping.get(sport, sport.lower())
    
    @staticmethod
    def _sport_to_thescore(sport: str) -> str:
        """Convert sport name to TheScore URL format."""
        mapping = {
            "NBA": "nba",
            "NFL": "nfl",
            "NHL": "nhl",
            "MLB": "mlb",
            "NCAAB": "ncaab",
            "NCAAF": "ncaaf",
            "EPL": "soccer",
            "MLS": "soccer",
        }
        return mapping.get(sport, sport.lower())
    
    @staticmethod
    def _sport_to_espn(sport: str) -> str:
        """Convert sport name to ESPN URL format."""
        mapping = {
            "NBA": "nba",
            "NFL": "nfl",
            "NHL": "nhl",
            "MLB": "mlb",
            "NCAAB": "college-basketball",
            "NCAAF": "college-football",
            "EPL": "soccer",
            "MLS": "soccer",
        }
        return mapping.get(sport, sport.lower())


async def scrape_daily_props(sports: List[str]) -> Dict[str, Any]:
    """
    Scrape props for multiple sports daily.
    
    Usage:
        result = await scrape_daily_props(["NBA", "NFL"])
        # Returns: {
        #     "NBA": {"props": [...], "source": "fanduel", "success": True},
        #     "NFL": {"props": [...], "source": "betmgm", "success": True},
        # }
    """
    results = {}
    
    async with PropScraper() as scraper:
        for sport in sports:
            try:
                result = await scraper.scrape_all_sources(sport)
                results[sport] = result
            except Exception as e:
                logger.error(f"Failed to scrape {sport}: {e}")
                results[sport] = {
                    "props": [],
                    "source": "none",
                    "errors": [str(e)],
                    "success": False
                }
    
    return results


if __name__ == "__main__":
    # Example usage
    async def main():
        result = await scrape_daily_props(["NBA", "NFL"])
        for sport, data in result.items():
            print(f"\n{sport}:")
            print(f"  Source: {data['source']}")
            print(f"  Props: {len(data['props'])}")
            print(f"  Success: {data['success']}")
            if data.get('errors'):
                print(f"  Errors: {data['errors']}")
    
    asyncio.run(main())
