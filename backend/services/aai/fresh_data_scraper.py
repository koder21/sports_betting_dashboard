"""
Comprehensive fresh data scraper for AAI bets.
Fetches ALL fresh data needed for optimal betting recommendations.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ...models.games_upcoming import GameUpcoming
from ...models.games_live import GameLive
from ...models.injury import Injury
from ...models.team import Team
from ..espn_client import ESPNClient
from ..weather import WeatherService


def parse_iso_datetime(dt_string: str) -> Optional[datetime]:
    """Parse ISO 8601 datetime string to datetime object."""
    if not dt_string:
        return None
    try:
        # Handle ISO format like "2026-02-10T00:00Z"
        if dt_string.endswith('Z'):
            dt_string = dt_string[:-1] + '+00:00'
        return datetime.fromisoformat(dt_string)
    except:
        return None


class FreshDataScraper:
    """
    Scrapes all fresh data needed for AAI betting recommendations:
    - Today's games from ESPN (all sports)
    - Injuries for all teams
    - Weather forecasts for outdoor venues
    - Game odds
    - Team form/ELO updates
    """
    
    SPORTS = [
        ("basketball", "nba", "NBA"),
        ("basketball", "mens-college-basketball", "NCAAB"),
        ("football", "nfl", "NFL"),
        ("hockey", "nhl", "NHL"),
        ("soccer", "eng.1", "EPL"),
    ]
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.espn_client = ESPNClient()
        self.weather_service = WeatherService()
        self.team_espn_ids = []  # Store team ESPN IDs during game scraping
        
    async def scrape_all_fresh_data(self) -> Dict[str, Any]:
        """
        Main entry point - scrapes everything fresh.
        Returns summary of what was updated.
        """
        start_time = datetime.now(timezone.utc)
        
        print("🚀 Starting fresh data scrape...")
        
        # Run scraping tasks with individual error handling
        games_count = 0
        injuries_count = 0
        weather_count = 0
        errors = []
        
        try:
            games_count = await self._scrape_todays_games()
        except Exception as e:
            errors.append(f"Games: {str(e)[:100]}")
            print(f"  ❌ Games scrape failed: {e}")
        
        try:
            injuries_count = await self._scrape_injuries()
        except Exception as e:
            errors.append(f"Injuries: {str(e)[:100]}")
            print(f"  ❌ Injuries scrape failed: {e}")
        
        try:
            weather_count = await self._update_weather()
        except Exception as e:
            errors.append(f"Weather: {str(e)[:100]}")
            print(f"  ❌ Weather scrape failed: {e}")
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        summary = {
            "success": len(errors) == 0,
            "scraped_at": start_time.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "games_updated": games_count,
            "injuries_updated": injuries_count,
            "weather_forecasts": weather_count,
            "errors": errors,
            "message": f"✅ Data scraped in {elapsed:.1f}s" if not errors else f"⚠️ Partial scrape in {elapsed:.1f}s ({len(errors)} errors)"
        }
        
        print(f"\n{summary['message']}")
        print(f"  📅 Games: {games_count}")
        print(f"  🏥 Injuries: {injuries_count}")
        print(f"  🌦️ Weather: {weather_count}")
        if errors:
            print(f"  ⚠️ Errors: {len(errors)}")
        
        return summary
    
    async def _scrape_todays_games(self) -> int:
        """Scrape today's games from ESPN for all sports."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        
        total_games = 0
        # Store team ESPN IDs for injury scraping
        self.team_espn_ids = []
        
        for sport_type, league, sport_name in self.SPORTS:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={today}"
            data = await self.espn_client.get_json(url)
            
            if not data:
                continue
            
            events = data.get("events", [])
            
            for event in events:
                game_id = event.get("id")
                status = event.get("status", {})
                status_type = status.get("type", {}).get("name", "")
                
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                
                home_team = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_team = next((c for c in competitors if c.get("homeAway") == "away"), None)
                
                if not home_team or not away_team:
                    continue
                
                home_name = home_team.get("team", {}).get("displayName", "")
                away_name = away_team.get("team", {}).get("displayName", "")
                home_espn_id = home_team.get("team", {}).get("id")
                away_espn_id = away_team.get("team", {}).get("id")
                home_score = int(home_team.get("score", 0) or 0)
                away_score = int(away_team.get("score", 0) or 0)
                
                start_time_str = event.get("date", "")
                
                # Store ESPN IDs for injury scraping later
                if home_espn_id:
                    self.team_espn_ids.append((home_espn_id, home_name, sport_name))
                if away_espn_id:
                    self.team_espn_ids.append((away_espn_id, away_name, sport_name))
                
                # Upsert to games_upcoming if scheduled
                if status_type in ("STATUS_SCHEDULED", "STATUS_POSTPONED"):
                    await self._upsert_upcoming_game(
                        game_id=game_id,
                        sport=sport_name,
                        home_team=home_name,
                        away_team=away_name,
                        start_time=start_time_str,
                        status=status_type
                    )
                    total_games += 1
                
                # Upsert to games_live if in progress
                elif status_type == "STATUS_IN_PROGRESS":
                    await self._upsert_live_game(
                        game_id=game_id,
                        sport=sport_name,
                        home_team=home_name,
                        away_team=away_name,
                        home_score=home_score,
                        away_score=away_score
                    )
                    total_games += 1
        
        await self.session.commit()
        return total_games
    
    async def _upsert_upcoming_game(
        self,
        game_id: str,
        sport: str,
        home_team: str,
        away_team: str,
        start_time: str,
        status: str
    ):
        """Insert or update upcoming game."""
        # Parse start_time string to datetime object
        start_dt = parse_iso_datetime(start_time)
        
        # Check if exists
        stmt = select(GameUpcoming).where(GameUpcoming.game_id == game_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.home_team_name = home_team
            existing.away_team_name = away_team
            existing.start_time = start_dt
            existing.status = status
        else:
            new_game = GameUpcoming(
                game_id=game_id,
                sport=sport,
                home_team_name=home_team,
                away_team_name=away_team,
                start_time=start_dt,
                status=status
            )
            self.session.add(new_game)
    
    async def _upsert_live_game(
        self,
        game_id: str,
        sport: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int
    ):
        """Insert or update live game."""
        stmt = select(GameLive).where(GameLive.game_id == game_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.home_team_name = home_team
            existing.away_team_name = away_team
            existing.home_score = home_score
            existing.away_score = away_score
            existing.last_updated = datetime.now(timezone.utc)
        else:
            new_game = GameLive(
                game_id=game_id,
                sport=sport,
                home_team_name=home_team,
                away_team_name=away_team,
                home_score=home_score,
                away_score=away_score,
                last_updated=datetime.now(timezone.utc)
            )
            self.session.add(new_game)
    
    async def _scrape_injuries(self) -> int:
        """Scrape injuries for all teams playing today."""
        # Use the ESPN team IDs collected during game scraping
        if not self.team_espn_ids:
            print("  ⚠️ No team ESPN IDs found - skipping injuries")
            return 0
        
        # Deduplicate team IDs
        unique_teams = list(set(self.team_espn_ids))
        print(f"  🔍 Checking injuries for {len(unique_teams)} teams...")
        
        total_injuries = 0
        
        for espn_id, team_name, sport in unique_teams:
            # Determine the league path based on sport
            if sport == "NBA":
                league_path = "basketball/leagues/nba"
            elif sport == "NHL":
                league_path = "hockey/leagues/nhl"
            elif sport == "NFL":
                league_path = "football/leagues/nfl"
            elif sport == "NCAAB":
                league_path = "basketball/leagues/mens-college-basketball"
            else:
                continue
            
            # Fetch injuries using ESPN's v2 API
            injuries = await self._fetch_team_injuries_v2(espn_id, team_name, league_path)
            total_injuries += len(injuries)
            
            # Upsert each injury
            for injury_data in injuries:
                await self._upsert_injury(injury_data)
        
        await self.session.commit()
        print(f"  ✅ Found {total_injuries} total injuries")
        return total_injuries
    
    async def _fetch_team_injuries_v2(self, team_espn_id: str, team_name: str, league_path: str) -> List[Dict]:
        """Fetch injuries for a team using ESPN's v2 API (with nested refs)."""
        try:
            # First, get the list of injury references (with generous timeout)
            url = f"https://sports.core.api.espn.com/v2/sports/{league_path}/teams/{team_espn_id}/injuries"
            data = await asyncio.wait_for(
                self.espn_client.get_json(url),
                timeout=15.0  # 15 second timeout
            )
            
            if not data or "items" not in data:
                return []
            
            injuries = []
            
            # Get ALL injuries - don't limit
            items = data.get("items", [])
            
            # Fetch each injury detail from the nested reference
            for item in items:
                try:
                    ref_url = item.get("$ref")
                    if not ref_url:
                        continue
                    
                    injury_detail = await asyncio.wait_for(
                        self.espn_client.get_json(ref_url),
                        timeout=10.0  # 10 second timeout per injury
                    )
                    if not injury_detail:
                        continue
                    
                    # Extract athlete info from the nested athlete reference
                    athlete_ref = injury_detail.get("athlete", {}).get("$ref")
                    player_id = None
                    player_name = "Unknown"
                    
                    if athlete_ref:
                        try:
                            athlete_data = await asyncio.wait_for(
                                self.espn_client.get_json(athlete_ref),
                                timeout=10.0  # 10 second timeout per athlete
                            )
                            if athlete_data:
                                player_id = str(athlete_data.get("id", ""))
                                player_name = athlete_data.get("displayName", "Unknown")
                        except asyncio.TimeoutError:
                            pass  # Use default values
                    
                    # Build injury record
                    status = injury_detail.get("status", "Unknown")
                    details = injury_detail.get("details", {})
                    injury_type = details.get("type", "Unknown")
                    location = details.get("location", "")
                    detail = details.get("detail", "")
                    
                    description = f"{injury_type}"
                    if location:
                        description += f" ({location})"
                    if detail:
                        description += f" - {detail}"
                    
                    # Use team_espn_id as team_id since we don't have internal team_ids
                    injuries.append({
                        "player_id": player_id or player_name,  # Fallback to name if no ID
                        "team_id": team_espn_id,  # Use ESPN ID directly
                        "status": status,
                        "description": description,
                        "last_updated": datetime.now(timezone.utc)
                    })
                    
                    print(f"    🏥 {team_name}: {player_name} - {status} ({injury_type})")
                except (asyncio.TimeoutError, Exception) as e:
                    # Skip this injury if it fails but keep going
                    print(f"    ⚠️ Skipped one injury for {team_name}: {str(e)[:50]}")
                    continue
            
            return injuries
        except (asyncio.TimeoutError, Exception) as e:
            print(f"    ⚠️ {team_name}: Failed to fetch injuries ({str(e)[:50]})")
            return []
    
    async def _upsert_injury(self, injury_data: Dict):
        """Insert or update injury record."""
        # Check if exists
        stmt = select(Injury).where(
            Injury.player_id == injury_data["player_id"],
            Injury.team_id == injury_data["team_id"]
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.status = injury_data["status"]
            existing.description = injury_data["description"]
            existing.last_updated = injury_data["last_updated"]
        else:
            new_injury = Injury(**injury_data)
            self.session.add(new_injury)
    
    async def _update_weather(self) -> int:
        """Update weather forecasts for all outdoor games."""
        # Get all upcoming games
        stmt = select(GameUpcoming)
        result = await self.session.execute(stmt)
        games = result.scalars().all()
        
        weather_count = 0
        
        for game in games:
            # Check if outdoor sport
            if game.sport not in ["NFL", "NCAAF", "MLB", "SOCCER"]:
                continue
            
            # Get weather forecast
            venue = game.home_team_name  # Simplified - use team name as venue
            weather_data = await self.weather_service.get_weather_for_venue(venue, game.start_time)
            
            if weather_data:
                # Update game with weather
                game.weather = str(weather_data)  # Store as JSON string
                weather_count += 1
        
        await self.session.commit()
        return weather_count
    
    async def close(self):
        """Clean up resources."""
        await self.espn_client.close()
