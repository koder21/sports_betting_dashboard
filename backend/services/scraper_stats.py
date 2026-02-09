"""
Player Stats Scraper - Fetches team rosters and player statistics from ESPN
Uses the proper ESPN API endpoints for reliable data fetching
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert

from .espn_client import ESPNClient
from ..models.player import Player
from ..models.player_stats import PlayerStats
from ..models.team import Team
from ..models.games_results import GameResult


class PlayerStatsScraper:
    """Scrapes player rosters and statistics from ESPN using dedicated endpoints"""
    
    SPORTS_CONFIG = [
        ("basketball", "nba", "NBA"),
        ("basketball", "mens-college-basketball", "NCAAB"),
        ("football", "nfl", "NFL"),
        ("hockey", "nhl", "NHL"),
    ]
    
    def __init__(self, client: ESPNClient, session: AsyncSession):
        self.client = client
        self.session = session
    
    async def scrape_teams_and_rosters(self):
        """Scrape team rosters and player info for all sports"""
        print("Scraping team rosters and players...")
        
        total_teams = 0
        total_players = 0
        
        for sport_type, league, sport_name in self.SPORTS_CONFIG:
            try:
                print(f"\n{sport_name}:")
                
                # Get all teams for this sport
                teams_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/teams?limit=100"
                teams_data = await self.client.get_json(teams_url)
                
                if not teams_data or "sports" not in teams_data:
                    print(f"  No teams data found")
                    continue
                
                # Navigate the ESPN teams structure
                teams = []
                for sport in teams_data.get("sports", []):
                    for league_data in sport.get("leagues", []):
                        teams.extend(league_data.get("teams", []))
                
                print(f"  Found {len(teams)} teams")
                
                for team_data in teams:
                    team_info = team_data.get("team", {})
                    team_espn_id = str(team_info.get("id"))
                    team_name = team_info.get("displayName")
                    
                    if not team_espn_id:
                        continue
                    
                    # Create unique team_id by prefixing with sport (ESPN reuses IDs across sports)
                    team_id = f"{sport_name}-{team_espn_id}"
                    
                    # Upsert team first
                    await self._upsert_team(
                        team_id=team_id,
                        name=team_name,
                        abbreviation=team_info.get("abbreviation"),
                        sport_name=sport_name,
                        league=league,
                    )
                    
                    # Fetch team roster - using site.api.espn.com which supports enable=roster
                    roster_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/teams/{team_espn_id}?enable=roster"
                    roster_data = await self.client.get_json(roster_url)
                    
                    if not roster_data:
                        continue
                    
                    roster = roster_data.get("team", {}).get("athletes", [])
                    print(f"    {team_name}: {len(roster)} players")
                    
                    for athlete in roster:
                        player_id = str(athlete.get("id"))
                        player_name = (
                            athlete.get("displayName")
                            or athlete.get("fullName")
                            or athlete.get("shortName")
                        )
                        
                        if not player_id:
                            continue
                        
                        # Upsert player
                        await self._upsert_player(
                            player_id=player_id,
                            name=athlete.get("displayName"),
                            position=athlete.get("position", {}).get("abbreviation") if isinstance(athlete.get("position"), dict) else athlete.get("position"),
                            team_id=team_id,
                            sport=sport_name,
                            league=league,
                            headshot=athlete.get("headshot", {}).get("href") if isinstance(athlete.get("headshot"), dict) else None,
                            jersey=athlete.get("jersey"),
                        )
                        total_players += 1
                    
                    total_teams += 1
                
            except Exception as e:
                print(f"  Error scraping {sport_name}: {e}")
                continue
        
        await self.session.commit()
        print(f"\nRoster scraping complete: {total_teams} teams, {total_players} players")
    
    async def scrape_player_stats(self, season_year: int = 2026):
        """Scrape season stats for all players using the stats API endpoint"""
        print(f"\nScraping player season stats for {season_year}...")
        
        total_stats = 0
        
        # Get all players from database
        result = await self.session.execute(
            select(Player).where(Player.active == True)
        )
        players = result.scalars().all()
        
        print(f"Found {len(players)} active players to fetch stats for")
        
        for player in players:
            try:
                # Use the dedicated stats endpoint
                # Format: site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/stats
                sport_type_map = {
                    "NBA": ("basketball", "nba"),
                    "NCAAB": ("basketball", "mens-college-basketball"),
                    "NFL": ("football", "nfl"),
                    "NHL": ("hockey", "nhl"),
                }
                
                if player.sport not in sport_type_map:
                    continue
                
                sport_type, league = sport_type_map[player.sport]
                
                stats_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport_type}/{league}/athletes/{player.player_id}/stats"
                stats_data = await self.client.get_json(stats_url)
                
                if not stats_data:
                    continue
                
                # Parse season stats - structure varies by sport
                # Typically: splits.categories[].stats[]
                await self._parse_and_save_season_stats(player, stats_data, season_year)
                total_stats += 1
                
                if total_stats % 50 == 0:
                    print(f"  Processed {total_stats} players...")
                    await self.session.commit()
                
            except Exception as e:
                # Don't log every error, too verbose
                pass
        
        await self.session.commit()
        print(f"Stats scraping complete: {total_stats} players with stats")
    
    async def _parse_and_save_season_stats(self, player: Player, stats_data: Dict, season_year: int):
        """Parse stats API response and save season averages"""
        # This is complex because ESPN stats structure varies by sport
        # For now, we'll skip this and focus on game logs which are more useful
        pass
    
    async def scrape_recent_games(self, days_back: int = 7):
        """Main entry point - scrape rosters first, then recent game stats"""
        effective_days_back = days_back
        last_scrape_date = await self._get_last_stats_scrape_date()
        if last_scrape_date:
            today = datetime.now(timezone.utc).date()
            delta_days = (today - last_scrape_date).days
            effective_days_back = max(1, delta_days + 1)  # 1 day padding

        # First, get all team rosters and players (weekly)
        should_scrape_rosters = True
        last_roster_date = await self._get_last_roster_scrape_date()
        if last_roster_date:
            today = datetime.now(timezone.utc).date()
            should_scrape_rosters = (today - last_roster_date).days >= 7

        if should_scrape_rosters:
            await self.scrape_teams_and_rosters()
            await self._set_last_roster_scrape_date(datetime.now(timezone.utc).date())
        else:
            print("Skipping roster scrape (last run within 7 days)")
        
        # Then scrape recent game stats from boxscores
        print(f"\nScraping game stats from last {effective_days_back} days...")
        
        total_stats = 0
        
        for sport_type, league, sport_name in self.SPORTS_CONFIG:
            try:
                game_ids = await self._get_recent_game_ids(sport_type, league, effective_days_back)
                print(f"{sport_name}: Found {len(game_ids)} completed games")
                
                for game_id in game_ids:
                    stats_added = await self._scrape_game_boxscore(
                        game_id, sport_type, league, sport_name
                    )
                    total_stats += stats_added
                
            except Exception as e:
                print(f"Error scraping {sport_name} game stats: {e}")
                continue
        
        await self.session.commit()
        await self._set_last_stats_scrape_date(datetime.now(timezone.utc).date())
        print(f"Game stats scraping complete: {total_stats} stat records")

    async def _get_last_stats_scrape_date(self) -> Optional[date]:
        """Get last successful stats scrape date from scraper_state table"""
        await self.session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS scraper_state (key TEXT PRIMARY KEY, value TEXT)"
            )
        )
        result = await self.session.execute(
            text("SELECT value FROM scraper_state WHERE key = :key"),
            {"key": "player_stats_last_scrape"},
        )
        row = result.first()
        if row and row[0]:
            try:
                return datetime.fromisoformat(row[0]).date()
            except Exception:
                return None
        return None

    async def _get_last_roster_scrape_date(self) -> Optional[date]:
        """Get last successful roster scrape date from scraper_state table"""
        await self.session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS scraper_state (key TEXT PRIMARY KEY, value TEXT)"
            )
        )
        result = await self.session.execute(
            text("SELECT value FROM scraper_state WHERE key = :key"),
            {"key": "player_rosters_last_scrape"},
        )
        row = result.first()
        if row and row[0]:
            try:
                return datetime.fromisoformat(row[0]).date()
            except Exception:
                return None
        return None

    async def _set_last_stats_scrape_date(self, date_value) -> None:
        """Persist last successful stats scrape date"""
        await self.session.execute(
            text(
                """
                INSERT INTO scraper_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            ),
            {"key": "player_stats_last_scrape", "value": date_value.isoformat()},
        )
        await self.session.commit()

    async def _set_last_roster_scrape_date(self, date_value) -> None:
        """Persist last successful roster scrape date"""
        await self.session.execute(
            text(
                """
                INSERT INTO scraper_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            ),
            {"key": "player_rosters_last_scrape", "value": date_value.isoformat()},
        )
        await self.session.commit()
    
    async def _get_recent_game_ids(self, sport_type: str, league: str, days_back: int) -> List[str]:
        """Get game IDs from recent days"""
        game_ids = []
        
        for days_ago in range(days_back):
            date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={date}"
            
            try:
                data = await self.client.get_json(url)
                if not data:
                    continue
                
                events = data.get("events", [])
                
                for event in events:
                    status = event.get("status", {}).get("type", {}).get("name", "")
                    # Only process completed games
                    if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                        game_ids.append(event.get("id"))
            except Exception as e:
                continue
        
        return game_ids
    
    async def _scrape_game_boxscore(
        self, game_id: str, sport_type: str, league: str, sport_name: str
    ) -> int:
        """Scrape boxscore for a single game and save player stats"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
        
        try:
            data = await self.client.get_json(url)
            if not data or "boxscore" not in data:
                return 0

            # Upsert final game result (history scraper)
            await self._upsert_game_result(
                data=data,
                game_id=game_id,
                sport_name=sport_name,
                league=league,
            )
            
            boxscore = data["boxscore"]
            stats_added = 0
            
            # ESPN player stats are at boxscore.players
            players_by_team = boxscore.get("players", [])
            
            for team_players in players_by_team:
                team_info = team_players.get("team", {})
                team_id = team_info.get("id")
                
                statistics_groups = team_players.get("statistics", [])
                
                for stat_group in statistics_groups:
                    stat_type = stat_group.get("name", "")  # 'passing', 'rushing', 'receiving', etc.
                    stat_labels = stat_group.get("labels", [])
                    athletes = stat_group.get("athletes", [])
                    
                    for athlete_data in athletes:
                        athlete = athlete_data.get("athlete", {})
                        stats = athlete_data.get("stats", [])
                        
                        if not athlete:
                            continue
                        
                        player_id = str(athlete.get("id"))
                        
                        # Save stats for this game
                        stat_added = await self._save_player_stats(
                            game_id=game_id,
                            player_id=player_id,
                            player_name=player_name,
                            team_id=str(team_id) if team_id else None,
                            sport=sport_name,
                            league=league,
                            stats_list=stats,
                            stat_type=stat_type,
                            stat_labels=stat_labels,
                        )
                        if stat_added:
                            stats_added += 1
            
            return stats_added
            
        except Exception as e:
            return 0

    async def _upsert_game_result(
        self,
        data: Dict[str, Any],
        game_id: str,
        sport_name: str,
        league: str,
    ) -> None:
        """Upsert final game results into games_results without duplicates."""
        try:
            header = data.get("header", {})
            competitions = header.get("competitions") or data.get("competitions") or []
            comp = competitions[0] if competitions else {}

            status_type = (comp.get("status", {}).get("type", {}) or {})
            status_name = status_type.get("name") or ""
            status_detail = status_type.get("detail") or status_name

            # Only insert final games
            if status_name and status_name not in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                return

            def parse_datetime(value: Optional[str]) -> Optional[datetime]:
                if not value:
                    return None
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except Exception:
                    return None

            start_time = parse_datetime(comp.get("date") or header.get("date"))

            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)

            def team_id_for(comp_team: Optional[Dict[str, Any]]) -> Optional[str]:
                team = (comp_team or {}).get("team", {})
                espn_id = team.get("id")
                if not espn_id:
                    return None
                return f"{sport_name}-{espn_id}"

            def team_name_for(comp_team: Optional[Dict[str, Any]]) -> Optional[str]:
                team = (comp_team or {}).get("team", {})
                return team.get("displayName") or team.get("shortDisplayName")

            def team_logo_for(comp_team: Optional[Dict[str, Any]]) -> Optional[str]:
                team = (comp_team or {}).get("team", {})
                logo = team.get("logo")
                if logo:
                    return logo
                logos = team.get("logos") or []
                if logos:
                    return logos[0].get("href") or logos[0].get("url")
                return None

            def score_for(comp_team: Optional[Dict[str, Any]]) -> Optional[int]:
                score = (comp_team or {}).get("score")
                try:
                    return int(score) if score is not None else None
                except Exception:
                    return None

            season = header.get("season", {}) or comp.get("season", {}) or {}
            season_year = season.get("year")
            season_type = season.get("type")

            attendance = comp.get("attendance")
            officials = comp.get("officials") or []
            referees = ", ".join([
                o.get("fullName") for o in officials if o.get("fullName")
            ]) or None

            weather = None
            weather_obj = comp.get("weather") or {}
            if weather_obj:
                weather = weather_obj.get("displayValue") or weather_obj.get("shortDisplayValue")

            venue = (comp.get("venue") or {}).get("fullName")

            stmt = insert(GameResult).values(
                game_id=game_id,
                sport=sport_name,
                league=league,
                season=str(season_year) if season_year else None,
                season_type=str(season_type) if season_type else None,
                start_time=start_time,
                end_time=None,
                venue=venue,
                home_team_id=team_id_for(home),
                away_team_id=team_id_for(away),
                home_team_name=team_name_for(home),
                away_team_name=team_name_for(away),
                home_logo=team_logo_for(home),
                away_logo=team_logo_for(away),
                home_score=score_for(home),
                away_score=score_for(away),
                status=status_detail or status_name,
                attendance=attendance,
                referees=referees,
                weather=weather,
                moved_at=None,
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=["game_id"],
                set_={
                    "sport": sport_name,
                    "league": league,
                    "season": str(season_year) if season_year else None,
                    "season_type": str(season_type) if season_type else None,
                    "start_time": start_time,
                    "venue": venue,
                    "home_team_id": team_id_for(home),
                    "away_team_id": team_id_for(away),
                    "home_team": team_name_for(home),
                    "away_team": team_name_for(away),
                    "home_logo": team_logo_for(home),
                    "away_logo": team_logo_for(away),
                    "home_score": score_for(home),
                    "away_score": score_for(away),
                    "status": status_detail or status_name,
                    "attendance": attendance,
                    "referees": referees,
                    "weather": weather,
                },
            )

            await self.session.execute(stmt)
        except Exception:
            return
    
    async def _upsert_team(
        self,
        team_id: str,
        name: Optional[str],
        abbreviation: Optional[str],
        sport_name: str,
        league: str,
    ) -> bool:
        """Upsert team to database"""
        try:
            stmt = insert(Team).values(
                team_id=team_id,
                name=name,
                abbreviation=abbreviation,
                sport_name=sport_name,
                league=league,
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=["team_id"],
                set_=dict(
                    name=name,
                    abbreviation=abbreviation,
                    sport_name=sport_name,
                    league=league,
                )
            )
            
            await self.session.execute(stmt)
            return True
        except Exception as e:
            return False
    
    async def _upsert_player(
        self,
        player_id: str,
        name: Optional[str],
        position: Optional[str],
        team_id: Optional[str],
        sport: str,
        league: str,
        headshot: Optional[str],
        jersey: Optional[str],
    ) -> bool:
        """Upsert player to database with retry logic for database locks"""
        import asyncio
        from sqlalchemy.exc import OperationalError
        
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms delay
        
        for attempt in range(max_retries):
            try:
                stmt = insert(Player).values(
                    player_id=player_id,
                    espn_id=player_id,
                    full_name=name,
                    name=name,
                    position=position,
                    team_id=team_id,
                    sport=sport,
                    league=league,
                    headshot=headshot,
                    jersey=jersey,
                    active=True,
                )
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=["player_id"],
                    set_=dict(
                        full_name=name,
                        name=name,
                        position=position,
                        team_id=team_id,
                        headshot=headshot,
                        jersey=jersey,
                        active=True,
                    )
                )
                
                await self.session.execute(stmt)
                return True
                
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    # Exponential backoff: wait before retrying
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Double the delay each retry
                    continue
                else:
                    print(f"Error upserting player {player_id}: {e}")
                    return False
            except Exception as e:
                print(f"Error upserting player {player_id}: {e}")
                return False
        
        return False
    
    async def _save_player_stats(
        self,
        game_id: str,
        player_id: str,
        player_name: Optional[str],
        team_id: Optional[str],
        sport: str,
        league: str,
        stats_list: List[str],
        stat_type: str = "",
        stat_labels: Optional[List[str]] = None,
    ) -> bool:
        """Parse stats array and save to database"""
        try:
            # LONG-TERM FIX: Ensure player exists before saving stats
            from ..models.player import Player
            player_check = await self.session.execute(
                select(Player).where(Player.player_id == player_id)
            )
            existing_player = player_check.scalar_one_or_none()
            if not existing_player:
                # Create player using real name if available
                resolved_name = player_name or f"Player {player_id}"
                placeholder_player = Player(
                    player_id=player_id,
                    name=resolved_name,
                    sport=sport,
                )
                self.session.add(placeholder_player)
                await self.session.flush()
            elif player_name and existing_player.name and existing_player.name.startswith("Player "):
                # Upgrade placeholder name to real name when available
                existing_player.name = player_name
                await self.session.flush()
            
            # Check if stats already exist for this game/player
            result = await self.session.execute(
                select(PlayerStats).where(
                    PlayerStats.game_id == game_id,
                    PlayerStats.player_id == player_id
                )
            )
            existing = result.scalar_one_or_none()
            
            # Parse stats based on sport and stat type
            parsed_stats = self._parse_stats(sport, stats_list, stat_type, stat_labels or [])
            
            if existing:
                # Update existing record with new stats (merge with existing)
                for key, value in parsed_stats.items():
                    if value is not None:
                        setattr(existing, key, value)
                await self.session.flush()  # Flush to ensure subsequent queries see the updates
                return True
            else:
                # Create new stats record
                stats_record = PlayerStats(
                    game_id=game_id,
                    player_id=player_id,
                    team_id=team_id,
                    sport=sport,
                    league=league,
                    **parsed_stats
                )
            
                self.session.add(stats_record)
                await self.session.flush()  # Flush to ensure subsequent queries can find this record
                return True
        except Exception as e:
            print(f"Error saving stats for player {player_id}: {e}")
            return False
    
    def _parse_stats(self, sport: str, stats_list: List[str], stat_type: str = "", stat_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Parse ESPN stats array into database columns"""
        parsed = {}
        stat_labels = stat_labels or []
        
        if sport in ["NBA", "NCAAB"]:
            # Basketball stats format from ESPN: [MIN, PTS, FG, 3PT, FT, REB, AST, TO, STL, BLK, OREB, DREB, PF, +/-]
            # Use labels to map correctly
            label_map = {label.upper(): i for i, label in enumerate(stat_labels)}
            
            if 'MIN' in label_map and len(stats_list) > label_map['MIN']:
                parsed["minutes"] = stats_list[label_map['MIN']] if stats_list[label_map['MIN']] else None
            if 'PTS' in label_map and len(stats_list) > label_map['PTS']:
                parsed["points"] = self._to_int(stats_list[label_map['PTS']])
            if 'FG' in label_map and len(stats_list) > label_map['FG']:
                parsed["fg"] = stats_list[label_map['FG']] if stats_list[label_map['FG']] else None
            if '3PT' in label_map and len(stats_list) > label_map['3PT']:
                parsed["three_pt"] = stats_list[label_map['3PT']] if stats_list[label_map['3PT']] else None
            if 'FT' in label_map and len(stats_list) > label_map['FT']:
                parsed["ft"] = stats_list[label_map['FT']] if stats_list[label_map['FT']] else None
            if 'REB' in label_map and len(stats_list) > label_map['REB']:
                parsed["rebounds"] = self._to_int(stats_list[label_map['REB']])
            if 'AST' in label_map and len(stats_list) > label_map['AST']:
                parsed["assists"] = self._to_int(stats_list[label_map['AST']])
            if 'STL' in label_map and len(stats_list) > label_map['STL']:
                parsed["steals"] = self._to_int(stats_list[label_map['STL']])
            if 'BLK' in label_map and len(stats_list) > label_map['BLK']:
                parsed["blocks"] = self._to_int(stats_list[label_map['BLK']])
            if 'TO' in label_map and len(stats_list) > label_map['TO']:
                parsed["turnovers"] = self._to_int(stats_list[label_map['TO']])
            if 'PF' in label_map and len(stats_list) > label_map['PF']:
                parsed["fouls"] = self._to_int(stats_list[label_map['PF']])
        
        elif sport in ["NFL", "NCAAF"]:
            # NFL/College Football stats vary by stat_type
            # Labels help us know what each value represents
            
            if stat_type == "passing":
                # Format: [C/ATT, YDS, AVG, TD, INT, SACKS, QBR, RTG]
                parsed["passing_yards"] = self._to_int(stats_list[1]) if len(stats_list) > 1 else None
                parsed["passing_tds"] = self._to_int(stats_list[3]) if len(stats_list) > 3 else None
                parsed["interceptions"] = self._to_int(stats_list[4]) if len(stats_list) > 4 else None
            
            elif stat_type == "rushing":
                # Format: [CAR, YDS, AVG, TD, LONG]
                parsed["rushing_yards"] = self._to_int(stats_list[1]) if len(stats_list) > 1 else None
                parsed["rushing_tds"] = self._to_int(stats_list[3]) if len(stats_list) > 3 else None
            
            elif stat_type == "receiving":
                # Format: [REC, YDS, AVG, TD, LONG, TGTS]
                parsed["receiving_yards"] = self._to_int(stats_list[1]) if len(stats_list) > 1 else None
                parsed["receiving_tds"] = self._to_int(stats_list[3]) if len(stats_list) > 3 else None
            
            elif stat_type == "defensive":
                # Format: [TOT, SOLO, SACKS, TFL, PD, QB HTS, TD]
                parsed["tackles"] = self._to_int(stats_list[0]) if len(stats_list) > 0 else None
                parsed["sacks"] = self._to_int(stats_list[2]) if len(stats_list) > 2 else None
        
        elif sport == "NHL":
            # Hockey stats format varies by position
            # Use labels to map correctly
            label_map = {label.upper(): i for i, label in enumerate(stat_labels)}
            
            # Check if this is goalie stats (stat_type will be "goaltending" or similar)
            if stat_type and "goalt" in stat_type.lower():
                # Goalie stats: [SA, GA, SV, SV%, TOI, PIM]
                if 'SV' in label_map and len(stats_list) > label_map['SV']:
                    parsed["goalie_saves"] = self._to_int(stats_list[label_map['SV']])
                elif 'SAVES' in label_map and len(stats_list) > label_map['SAVES']:
                    parsed["goalie_saves"] = self._to_int(stats_list[label_map['SAVES']])
                
                if 'GA' in label_map and len(stats_list) > label_map['GA']:
                    parsed["goalie_ga"] = self._to_int(stats_list[label_map['GA']])
                
                if 'SV%' in label_map and len(stats_list) > label_map['SV%']:
                    sv_pct_str = stats_list[label_map['SV%']]
                    if sv_pct_str and sv_pct_str not in ["--", "-"]:
                        try:
                            # Convert percentage string (e.g., "0.923" or "92.3%") to float
                            parsed["goalie_sv_pct"] = float(sv_pct_str.replace('%', ''))
                        except (ValueError, TypeError):
                            pass
            else:
                # Skater stats: [BS, HT, TK, +/-, TOI, PPTOI, SHTOI, ESTOI, SHFT, G, YTDG, A, S, SM, SOG, FW, FL, FO%, GV, PN, PIM]
                if 'G' in label_map and len(stats_list) > label_map['G']:
                    parsed["nhl_goals"] = self._to_int(stats_list[label_map['G']])
                if 'A' in label_map and len(stats_list) > label_map['A']:
                    parsed["nhl_assists"] = self._to_int(stats_list[label_map['A']])
                if 'SOG' in label_map and len(stats_list) > label_map['SOG']:
                    parsed["nhl_shots"] = self._to_int(stats_list[label_map['SOG']])
                if 'HT' in label_map and len(stats_list) > label_map['HT']:
                    parsed["nhl_hits"] = self._to_int(stats_list[label_map['HT']])
                if 'BS' in label_map and len(stats_list) > label_map['BS']:
                    parsed["nhl_blocks"] = self._to_int(stats_list[label_map['BS']])
                if '+/-' in label_map and len(stats_list) > label_map['+/-']:
                    parsed["nhl_plus_minus"] = self._to_int(stats_list[label_map['+/-']])
                
                # Calculate points from goals + assists for skaters only
                goals = parsed.get("nhl_goals") or 0
                assists = parsed.get("nhl_assists") or 0
                if goals > 0 or assists > 0:  # Only set points if there are goals or assists
                    parsed["points"] = goals + assists
        
        elif sport == "MLB":
            # Baseball stats - batting: [AB, R, H, RBI, HR, BB, SO, AVG, OBP, SLG]
            # Baseball stats - pitching: [IP, H, R, ER, BB, SO, HR, ERA]
            label_map = {label.upper(): i for i, label in enumerate(stat_labels)}
            
            if stat_type == "batting":
                if 'H' in label_map and len(stats_list) > label_map['H']:
                    parsed["hits"] = self._to_int(stats_list[label_map['H']])
                if 'R' in label_map and len(stats_list) > label_map['R']:
                    parsed["runs"] = self._to_int(stats_list[label_map['R']])
                if 'RBI' in label_map and len(stats_list) > label_map['RBI']:
                    parsed["rbi"] = self._to_int(stats_list[label_map['RBI']])
                if 'HR' in label_map and len(stats_list) > label_map['HR']:
                    parsed["hr"] = self._to_int(stats_list[label_map['HR']])
                if 'BB' in label_map and len(stats_list) > label_map['BB']:
                    parsed["bb"] = self._to_int(stats_list[label_map['BB']])
                if 'SO' in label_map and len(stats_list) > label_map['SO']:
                    parsed["so"] = self._to_int(stats_list[label_map['SO']])
            elif stat_type == "pitching":
                if 'IP' in label_map and len(stats_list) > label_map['IP']:
                    parsed["pitch_ip"] = stats_list[label_map['IP']] if stats_list[label_map['IP']] else None
                if 'SO' in label_map and len(stats_list) > label_map['SO']:
                    parsed["pitch_k"] = self._to_int(stats_list[label_map['SO']])
                elif 'K' in label_map and len(stats_list) > label_map['K']:
                    parsed["pitch_k"] = self._to_int(stats_list[label_map['K']])
                if 'BB' in label_map and len(stats_list) > label_map['BB']:
                    parsed["pitch_bb"] = self._to_int(stats_list[label_map['BB']])
                if 'ER' in label_map and len(stats_list) > label_map['ER']:
                    parsed["pitch_er"] = self._to_int(stats_list[label_map['ER']])
        
        elif sport in ["EPL", "SOCCER", "ENG.1"]:
            # Soccer stats vary by position
            label_map = {label.upper(): i for i, label in enumerate(stat_labels)}
            
            # Check if this is goalkeeper stats
            if stat_type and "goalk" in stat_type.lower():
                # Goalkeeper stats: [SAV, GA, SV%, PKS, etc.]
                if 'SAV' in label_map and len(stats_list) > label_map['SAV']:
                    parsed["epl_saves"] = self._to_int(stats_list[label_map['SAV']])
                elif 'SAVES' in label_map and len(stats_list) > label_map['SAVES']:
                    parsed["epl_saves"] = self._to_int(stats_list[label_map['SAVES']])
                elif 'SV' in label_map and len(stats_list) > label_map['SV']:
                    parsed["epl_saves"] = self._to_int(stats_list[label_map['SV']])
            else:
                # Field player stats (forwards, midfielders, defenders)
                if 'G' in label_map and len(stats_list) > label_map['G']:
                    parsed["epl_goals"] = self._to_int(stats_list[label_map['G']])
                if 'A' in label_map and len(stats_list) > label_map['A']:
                    parsed["epl_assists"] = self._to_int(stats_list[label_map['A']])
                if 'SOT' in label_map and len(stats_list) > label_map['SOT']:
                    parsed["epl_shots_on_target"] = self._to_int(stats_list[label_map['SOT']])
                if 'P' in label_map and len(stats_list) > label_map['P']:
                    parsed["epl_passes"] = self._to_int(stats_list[label_map['P']])
                elif 'PASS' in label_map and len(stats_list) > label_map['PASS']:
                    parsed["epl_passes"] = self._to_int(stats_list[label_map['PASS']])
                if 'T' in label_map and len(stats_list) > label_map['T']:
                    parsed["epl_tackles"] = self._to_int(stats_list[label_map['T']])
                elif 'TACKLES' in label_map and len(stats_list) > label_map['TACKLES']:
                    parsed["epl_tackles"] = self._to_int(stats_list[label_map['TACKLES']])
        
        return parsed
    
    def _to_int(self, value: str) -> Optional[int]:
        """Safely convert string to int"""
        try:
            if value and value != "--" and value != "-":
                return int(value)
        except (ValueError, TypeError):
            pass
        return None
