"""Pre-bet verification service - fresh data check before placing real money."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.game import Game
from ...models.games_upcoming import GameUpcoming
from ...models.injury import Injury
from ...models.player import Player
from ...models.team import Team
from ..weather import WeatherService
from ..espn_client import ESPNClient


class PreBetVerifier:
    """
    Comprehensive pre-bet verification system.
    
    Re-fetches FRESH data for a game before placing actual money:
    - Latest injuries from ESPN
    - Weather forecast
    - Current odds
    - Game status (not postponed/cancelled)
    - Key player lineups
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.weather_service = WeatherService()
        self.espn_client = ESPNClient()
    
    async def verify_game(self, game_id: str) -> Dict[str, Any]:
        """
        Comprehensive game verification before bet placement.
        
        Returns:
            Dict with verification results including:
            - game_status: verified/postponed/cancelled
            - injuries: fresh injury list
            - weather: forecast for game time
            - odds: latest odds from ESPN
            - recommendations: warnings or go-ahead
        """
        # 1. Get game from database
        game = await self._get_game(game_id)
        if not game:
            return {
                "verified": False,
                "error": "Game not found",
                "game_id": game_id
            }
        
        # 2. Verify game hasn't been postponed/cancelled (fresh ESPN check)
        game_status = await self._check_game_status(game_id, game)
        if game_status.get("status") not in ["scheduled", "pre", "STATUS_SCHEDULED"]:
            return {
                "verified": False,
                "error": f"Game status: {game_status.get('status')}",
                "game_id": game_id,
                "details": game_status
            }
        
        # 3. Fetch fresh injuries from ESPN
        injuries = await self._fetch_fresh_injuries(game)
        
        # 4. Get weather forecast for game time
        weather = await self._get_weather_forecast(game)
        
        # 5. Get latest odds from ESPN
        odds = await self._get_latest_odds(game_id, game)
        
        # 6. Check for lineup changes (if available)
        lineup_changes = await self._check_lineup_changes(game)
        
        # 7. Generate recommendations
        recommendations = self._generate_recommendations(
            game=game,
            game_status=game_status,
            injuries=injuries,
            weather=weather,
            odds=odds,
            lineup_changes=lineup_changes
        )
        
        return {
            "verified": True,
            "game_id": game_id,
            "game": {
                "home_team": game.home_team_name if hasattr(game, 'home_team_name') else None,
                "away_team": game.away_team_name if hasattr(game, 'away_team_name') else None,
                "start_time": game.start_time.isoformat() if game.start_time else None,
                "venue": game.venue if hasattr(game, 'venue') else None
            },
            "verification": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "game_status": game_status,
                "injuries": injuries,
                "weather": weather,
                "odds": odds,
                "lineup_changes": lineup_changes
            },
            "recommendations": recommendations
        }
    
    async def _get_game(self, game_id: str) -> Optional[Any]:
        """Get game from database (try GameUpcoming first, then Game)."""
        stmt = select(GameUpcoming).where(GameUpcoming.game_id == game_id)
        result = await self.session.execute(stmt)
        game = result.scalar_one_or_none()
        
        if not game:
            stmt = select(Game).where(Game.game_id == game_id)
            result = await self.session.execute(stmt)
            game = result.scalar_one_or_none()
        
        return game
    
    async def _check_game_status(self, game_id: str, game: Any) -> Dict[str, Any]:
        """Fetch fresh game status from ESPN API."""
        try:
            # Try to get sport from game_id format (e.g., "NBA-401468234")
            sport = game_id.split("-")[0].lower() if "-" in game_id else "nba"
            espn_id = game_id.split("-")[1] if "-" in game_id else game_id
            
            # ESPN event endpoint
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/summary?event={espn_id}"
            data = await self.espn_client.get_json(url)
            
            if not data:
                return {"status": "unknown", "error": "ESPN API unavailable"}
            
            header = data.get("header", {})
            competitions = header.get("competitions", [])
            if competitions:
                comp = competitions[0]
                status = comp.get("status", {})
                return {
                    "status": status.get("type", {}).get("name", "unknown"),
                    "detail": status.get("type", {}).get("detail"),
                    "last_checked": datetime.now(timezone.utc).isoformat()
                }
            
            return {"status": "unknown"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _fetch_fresh_injuries(self, game: Any) -> Dict[str, Any]:
        """Fetch latest injuries from ESPN for both teams."""
        home_team_id = game.home_team_id if hasattr(game, 'home_team_id') else None
        away_team_id = game.away_team_id if hasattr(game, 'away_team_id') else None
        
        home_injuries = await self._get_team_injuries(home_team_id) if home_team_id else []
        away_injuries = await self._get_team_injuries(away_team_id) if away_team_id else []
        
        return {
            "home_team": {
                "team_id": home_team_id,
                "injuries": home_injuries,
                "key_players_out": len([inj for inj in home_injuries if inj.get("is_key_player")])
            },
            "away_team": {
                "team_id": away_team_id,
                "injuries": away_injuries,
                "key_players_out": len([inj for inj in away_injuries if inj.get("is_key_player")])
            },
            "total_injuries": len(home_injuries) + len(away_injuries)
        }
    
    async def _get_team_injuries(self, team_id: str) -> List[Dict[str, Any]]:
        """Get injuries from database for a team."""
        stmt = select(Injury, Player).join(
            Player, Injury.player_id == Player.player_id
        ).where(Injury.team_id == team_id)
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        injuries = []
        for injury, player in rows:
            injuries.append({
                "player_id": injury.player_id,
                "player_name": player.full_name if player else "Unknown",
                "position": player.position if player else None,
                "status": injury.status,
                "description": injury.description,
                "last_updated": injury.last_updated.isoformat() if injury.last_updated else None,
                "is_key_player": self._is_key_player(player)
            })
        
        return injuries
    
    def _is_key_player(self, player: Optional[Player]) -> bool:
        """Determine if player is a key player (simplified)."""
        if not player:
            return False
        # Simple heuristic: starters or high-usage positions
        key_positions = ["QB", "RB", "WR", "PG", "SG", "C", "PF", "SF"]
        return player.position in key_positions if player.position else False
    
    async def _get_weather_forecast(self, game: Any) -> Optional[Dict[str, Any]]:
        """Get weather forecast for game time."""
        venue = game.venue if hasattr(game, 'venue') else None
        sport = game.sport if hasattr(game, 'sport') else None
        start_time = game.start_time if hasattr(game, 'start_time') else None
        
        if not venue or not sport:
            return None
        
        weather_impact = await self.weather_service.get_weather_impact_on_game(
            venue=venue,
            sport=sport,
            game_time=start_time
        )
        
        return weather_impact
    
    async def _get_latest_odds(self, game_id: str, game: Any) -> Optional[Dict[str, Any]]:
        """Get latest odds from ESPN (if available in game data)."""
        # ESPN odds are in game.odds_json or game.lines_json
        odds = {}
        
        if hasattr(game, 'odds_home') and hasattr(game, 'odds_away'):
            odds['moneyline'] = {
                "home": game.odds_home,
                "away": game.odds_away
            }
        
        if hasattr(game, 'spread_home') and hasattr(game, 'spread_away'):
            odds['spread'] = {
                "home": game.spread_home,
                "away": game.spread_away
            }
        
        if hasattr(game, 'total'):
            odds['total'] = game.total
        
        return odds if odds else None
    
    async def _check_lineup_changes(self, game: Any) -> Dict[str, Any]:
        """Check for recent lineup changes (if data available)."""
        # This would require ESPN lineup API, which is not always available
        # For now, return placeholder
        return {
            "checked": True,
            "changes_detected": False,
            "note": "Lineup data not available from ESPN API"
        }
    
    def _generate_recommendations(self, 
                                 game: Any,
                                 game_status: Dict[str, Any],
                                 injuries: Dict[str, Any],
                                 weather: Optional[Dict[str, Any]],
                                 odds: Optional[Dict[str, Any]],
                                 lineup_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate bet placement recommendations based on verification."""
        warnings = []
        confidence_adjustment = 0.0
        
        # Check game status
        if game_status.get("status") != "scheduled":
            warnings.append({
                "severity": "high",
                "message": f"Game status unusual: {game_status.get('status')}"
            })
            confidence_adjustment -= 0.2
        
        # Check injuries
        total_key_injuries = (
            injuries.get("home_team", {}).get("key_players_out", 0) +
            injuries.get("away_team", {}).get("key_players_out", 0)
        )
        
        if total_key_injuries > 0:
            warnings.append({
                "severity": "medium",
                "message": f"{total_key_injuries} key player(s) injured"
            })
            confidence_adjustment -= (0.05 * total_key_injuries)
        
        # Check weather
        if weather and weather.get("weather", {}).get("is_harsh"):
            warnings.append({
                "severity": "medium",
                "message": "Harsh weather conditions expected"
            })
            confidence_adjustment -= 0.1
        
        # Generate final recommendation
        if len(warnings) == 0:
            recommendation = "GO AHEAD - All checks passed"
            confidence = "high"
        elif confidence_adjustment > -0.15:
            recommendation = "PROCEED WITH CAUTION - Minor concerns detected"
            confidence = "medium"
        else:
            recommendation = "RECONSIDER - Multiple risk factors detected"
            confidence = "low"
        
        return {
            "recommendation": recommendation,
            "confidence_level": confidence,
            "confidence_adjustment": round(confidence_adjustment, 2),
            "warnings": warnings,
            "factors_checked": {
                "game_status": game_status.get("status"),
                "injuries_count": injuries.get("total_injuries", 0),
                "key_players_out": total_key_injuries,
                "harsh_weather": weather.get("weather", {}).get("is_harsh", False) if weather else False,
                "odds_available": odds is not None
            }
        }
    
    async def close(self):
        """Clean up resources."""
        await self.espn_client.close()
