"""
Prop bets scraper - fetches player prop odds from multiple sportsbooks.

Supported sources:
- ESPN (free, basic props)
- DraftKings API (requires research)
- FanDuel API (requires research)
- BetMGM (requires research)

Note: Most sportsbooks don't have public APIs for prop odds.
Alternative approaches:
1. Use Sportradar or The Odds API (paid services)
2. Web scraping (complex, fragile)
3. Manual entry for now, automated later
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.bet import Bet
from ..models.player import Player
from ..models.game import Game


class PropBetsScraper:
    """
    Scrape player prop odds from available sources.
    
    Current limitation: Most sportsbooks don't have public APIs.
    Recommending The Odds API (theoddsapi.com) for comprehensive prop coverage.
    """
    
    PROP_TYPES = {
        # NBA Props
        "player_points": "Player Points Over/Under",
        "player_assists": "Player Assists Over/Under",
        "player_rebounds": "Player Rebounds Over/Under",
        "player_3pm": "Player 3-Pointers Made",
        "player_steals": "Player Steals",
        "player_blocks": "Player Blocks",
        "player_prop_combo": "Player Props Combo",
        
        # NFL Props
        "player_passing_yards": "QB Passing Yards",
        "player_passing_td": "QB Passing TD",
        "player_rushing_yards": "RB Rushing Yards",
        "player_rushing_td": "RB Rushing TD",
        "player_receiving_yards": "WR Receiving Yards",
        "player_receiving_td": "WR Receiving TD",
        "player_tackles": "Player Tackles",
        "player_sacks": "Player Sacks",
        "player_interceptions": "Player Interceptions",
        
        # Soccer Props
        "player_goals": "Player Goals",
        "player_assists": "Player Assists",
        "player_shots": "Player Shots on Target",
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def scrape_espn_props(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Fetch basic props from ESPN (limited coverage).
        ESPN has limited prop odds, recommend using specialized API.
        """
        props = []
        # This would require parsing ESPN's specific prop endpoints
        # For now, return empty - ESPN props are limited
        return props
    
    async def scrape_from_odds_api(self, api_key: str, game_id: str, sport: str) -> List[Dict[str, Any]]:
        """
        Fetch prop odds from The Odds API (theoddsapi.com).
        
        Requires: API key from https://theoddsapi.com/
        Supports: Extensive prop coverage across all sports
        Cost: Free tier available, paid for more requests
        
        Note: This is the best free/paid option for prop odds.
        """
        if not api_key:
            return []
        
        props = []
        try:
            # This would call theoddsapi.com for prop odds
            # Would need to install aiohttp for async requests
            import aiohttp
            
            # Map sport names to odds API format
            sport_map = {
                "NBA": "basketball_nba",
                "NFL": "americanfootball_nfl",
                "NHL": "icehockey_nhl",
                "MLB": "baseball_mlb",
                "NCAAB": "basketball_ncaab",
                "NCAAF": "americanfootball_ncaaf",
            }
            
            odds_api_sport = sport_map.get(sport)
            if not odds_api_sport:
                return props
            
            # Construct URL for prop betting markets
            url = f"https://api.the-odds-api.com/v4/sports/{odds_api_sport}/events/{game_id}/odds"
            params = {
                "apiKey": api_key,
                "regions": "us",
                "markets": "player_props",  # Request prop markets
                "oddsFormat": "decimal"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse prop odds from response
                        # This would be customized based on API response format
                        
        except Exception as e:
            print(f"Error fetching from Odds API: {e}")
        
        return props
    
    def get_prop_recommendation_prompt(self) -> str:
        """
        Return guidance for prop bet integration.
        """
        return """
PROP BETS INTEGRATION GUIDE
===========================

RECOMMENDATION: Use The Odds API (https://theoddsapi.com/)
- Free tier: 500 requests/month
- Paid: $20+/month for more
- Coverage: All major sports and prop types
- Format: Clean JSON API

SETUP STEPS:
1. Sign up at https://theoddsapi.com/
2. Get API key
3. Add ODDS_API_KEY to .env
4. Uncomment/enable scrape_from_odds_api() in fresh_data_scraper.py
5. Add prop odds to AAI calculations

ALTERNATIVE: Manual Entry
- Create web UI for entering prop bets manually
- Store in dedicated props_manual table
- Include in AAI calculations

PROP TYPES SUPPORTED:
{prop_list}

INTEGRATION POINTS:
1. FreshDataScraper - Fetch props during refresh-and-calculate
2. AAIBetRecommender - Include props in recommendations
3. BetPlacementService - Allow placing prop bets as singles/parlays
4. Frontend - Display props in AAI results and game selector
"""


# Create helper for prop storage
class PropBet:
    """
    Data structure for a single prop bet.
    """
    def __init__(
        self,
        game_id: str,
        player_id: str,
        player_name: str,
        sport: str,
        prop_type: str,
        market: str,  # e.g., "Over 25.5" or "Under 4.5"
        over_odds: float,
        under_odds: float,
        source: str = "api"  # "api" or "manual"
    ):
        self.game_id = game_id
        self.player_id = player_id
        self.player_name = player_name
        self.sport = sport
        self.prop_type = prop_type
        self.market = market
        self.over_odds = over_odds
        self.under_odds = under_odds
        self.source = source
        self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "sport": self.sport,
            "prop_type": self.prop_type,
            "market": self.market,
            "over_odds": self.over_odds,
            "under_odds": self.under_odds,
            "source": self.source,
            "created_at": self.created_at.isoformat()
        }
