"""
Player Stats Scraper - Fetches team rosters and player statistics from ESPN
Uses the proper ESPN API endpoints for reliable data fetching
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta, date
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from backend.db import get_session
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from .espn_client import ESPNClient
from ..models.player import Player
from ..models.player_stats import PlayerStats
from ..models.team import Team
from ..models.games_results import GameResult



from contextlib import asynccontextmanager

class PlayerStatsScraper:
    """Scrapes player rosters and statistics from ESPN using dedicated endpoints"""

    async def close(self):
        if hasattr(self.client, 'close') and callable(self.client.close):
            await self.client.close()

    @classmethod
    @asynccontextmanager
    async def context(cls, *args, **kwargs):
        """Context manager to ensure ESPNClient session is closed after use."""
        scraper = cls(*args, **kwargs)
        try:
            yield scraper
        finally:
            await scraper.close()

    SPORTS_CONFIG = [
        ("basketball", "nba", "NBA"),
        ("basketball", "mens-college-basketball", "NCAAB"),
        ("football", "nfl", "NFL"),
        ("football", "college-football", "NCAAF"),
        ("hockey", "nhl", "NHL"),
        ("baseball", "mlb", "MLB"),
        ("soccer", "eng.1", "EPL"),
    ]
    
    def __init__(self, client: ESPNClient):
        self.client = client
    
    async def scrape_teams_and_rosters(self):
        async with get_session() as session:
            return await self._scrape_teams_and_rosters(session)

    async def _scrape_teams_and_rosters(self, session: AsyncSession):
        """Scrape team rosters and player info for all sports"""
        print("Scraping team rosters and players...")
        
        total_teams = 0
        total_players = 0
        
        # Fetch all sports teams concurrently instead of sequentially
        team_fetch_tasks = []
        sports_list = []
        
        for sport_type, league, sport_name in self.SPORTS_CONFIG:
            teams_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/teams?limit=100"
            team_fetch_tasks.append(self.client.get_json(teams_url))
            sports_list.append((sport_type, league, sport_name))
        
        # Fetch all team lists concurrently
        team_responses = await asyncio.gather(*team_fetch_tasks, return_exceptions=True)
        
        for (sport_type, league, sport_name), teams_data in zip(sports_list, team_responses):
            if isinstance(teams_data, Exception) or not teams_data:
                print(f"{sport_name}: Error fetching teams")
                continue
            
            try:
                if not isinstance(teams_data, dict) or "sports" not in teams_data:
                    print(f"{sport_name}: No teams data found")
                    continue
                # Navigate the ESPN teams structure
                teams = []
                for sport in teams_data.get("sports", []):
                    for league_data in sport.get("leagues", []):
                        teams.extend(league_data.get("teams", []))
                print(f"{sport_name}: Found {len(teams)} teams")
                
                # Fetch all rosters concurrently for this sport
                roster_tasks = []
                team_list = []
                
                for team_data in teams:
                    team_info = team_data.get("team", {})
                    team_espn_id = str(team_info.get("id"))
                    
                    if team_espn_id:
                        roster_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/teams/{team_espn_id}?enable=roster"
                        roster_tasks.append(self.client.get_json(roster_url))
                        team_list.append((team_data, sport_type, league, sport_name))
                
                # Fetch all rosters concurrently
                roster_responses = await asyncio.gather(*roster_tasks, return_exceptions=True)
                
                for team_data, roster_response in zip(team_list, roster_responses):
                    team_info_data, sport_type_i, league_i, sport_name_i = team_data
                    
                    if isinstance(roster_response, Exception) or not roster_response:
                        continue
                    
                    try:
                        team_info = team_info_data.get("team", {})
                        team_espn_id = str(team_info.get("id"))
                        team_name = team_info.get("displayName")
                        team_id = f"{sport_name_i}-{team_espn_id}"
                        
                        # Upsert team first
                        await self._upsert_team(
                            session=session,
                            team_id=team_id,
                            name=team_name,
                            abbreviation=team_info.get("abbreviation"),
                            sport_name=sport_name_i,
                            league=league_i,
                        )
                        
                        roster = roster_response.get("team", {}).get("athletes", []) if isinstance(roster_response, dict) else []
                        print(f"  {team_name}: {len(roster)} players")
                        
                        import logging
                        logger = logging.getLogger(__name__)
                        for athlete in roster:
                            player_id = str(athlete.get("id"))
                            player_name = athlete.get("displayName")
                            if not player_id:
                                logger.warning(f"[Roster Scrape] Missing player_id for athlete in team {team_name} ({team_id}), sport {sport_name_i}, league {league_i}")
                                continue
                            if not team_id:
                                logger.warning(f"[Roster Scrape] Missing team_id for player {player_id} ({player_name}), team context: {team_name}, sport {sport_name_i}, league {league_i}")
                                continue
                            # Upsert player
                            await self._upsert_player(
                                session=session,
                                player_id=player_id,
                                name=player_name,
                                position=athlete.get("position", {}).get("abbreviation") if isinstance(athlete.get("position"), dict) else athlete.get("position"),
                                team_id=team_id,
                                sport=sport_name_i,
                                league=league_i,
                                headshot=athlete.get("headshot", {}).get("href") if isinstance(athlete.get("headshot"), dict) else None,
                                jersey=athlete.get("jersey"),
                            )
                            total_players += 1
                        
                        total_teams += 1
                    except Exception as e:
                        print(f"    Error processing roster: {e}")
                        continue
                
            except Exception as e:
                print(f"  Error scraping {sport_name}: {e}")
                continue
        
        await session.commit()
        print(f"\nRoster scraping complete: {total_teams} teams, {total_players} players")
    
    async def scrape_player_stats(self, season_year: int = 2026):
        async with get_session() as session:
            return await self._scrape_player_stats(session, season_year)

    async def _scrape_player_stats(self, session: AsyncSession, season_year: int):
        """Scrape season stats for all players using the stats API endpoint"""
        print(f"\nScraping player season stats for {season_year}...")
        
        total_stats = 0
        
        # Get all players from database
        result = await session.execute(
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
                    await session.commit()
                
            except Exception as e:
                # Don't log every error, too verbose
                pass
        
        await session.commit()
        print(f"Stats scraping complete: {total_stats} players with stats")
    
    async def _parse_and_save_season_stats(self, player: Player, stats_data: Dict, season_year: int):
        """Parse stats API response and save season averages"""
        # This is complex because ESPN stats structure varies by sport
        # For now, we'll skip this and focus on game logs which are more useful
        pass
    
    async def scrape_recent_games(self, days_back: int = 7):
        """
        Scrape rosters (if needed) and all recent games' player stats using a single session per scrape.
        This ensures all DB writes for a game are committed in the same session, avoiding async/session bugs.
        """
        from backend.db import get_session
        import logging
        logger = logging.getLogger(__name__)
        async with get_session() as session:
            try:
                effective_days_back = days_back
                last_scrape_date = await self._get_last_stats_scrape_date(session)
                if last_scrape_date:
                    today = datetime.now(timezone.utc).date()
                    delta_days = (today - last_scrape_date).days
                    effective_days_back = max(1, delta_days + 1)  # 1 day padding

                should_scrape_rosters = True
                last_roster_date = await self._get_last_roster_scrape_date(session)
                if last_roster_date:
                    today = datetime.now(timezone.utc).date()
                    should_scrape_rosters = (today - last_roster_date).days >= 7

                if should_scrape_rosters:
                    await self._scrape_teams_and_rosters(session)
                    await self._set_last_roster_scrape_date(session, datetime.now(timezone.utc).date())
                else:
                    print("Skipping roster scrape (last run within 7 days)")

                print(f"\nScraping game stats from last {effective_days_back} days...")
                total_stats = 0

                # Collect all game IDs across all sports first (concurrent fetches)
                game_id_tasks = [
                    self._get_recent_game_ids(session, sport_type, league, effective_days_back)
                    for sport_type, league, sport_name in self.SPORTS_CONFIG
                ]
                all_game_id_results = await asyncio.gather(*game_id_tasks, return_exceptions=True)

                # Build flat list of (game_id, sport_type, league, sport_name)
                all_games = []
                for (sport_type, league, sport_name), game_ids in zip(self.SPORTS_CONFIG, all_game_id_results):
                    if isinstance(game_ids, Exception):
                        logger.error(f"Error fetching game ids for {sport_name}: {game_ids}")
                        continue
                    print(f"{sport_name}: Found {len(game_ids)} completed games")
                    for game_id in game_ids:
                        all_games.append((game_id, sport_type, league, sport_name))

                # Scrape all boxscores concurrently with a semaphore to limit load
                # Each game gets its own session to avoid shared-session conflicts
                semaphore = asyncio.Semaphore(8)

                async def scrape_one(game_id, sport_type, league, sport_name):
                    async with semaphore:
                        try:
                            async with get_session() as gsession:
                                count = await self._scrape_game_boxscore(
                                    gsession, game_id, sport_type, league, sport_name
                                )
                                await gsession.commit()
                                return count
                        except Exception as e:
                            logger.error(f"Error scraping boxscore for game {game_id}: {e}", exc_info=True)
                            return 0

                results = await asyncio.gather(
                    *(scrape_one(gid, st, lg, sn) for gid, st, lg, sn in all_games),
                    return_exceptions=True,
                )
                total_stats = sum(r for r in results if isinstance(r, int))
                print(f"Stats scraping complete: {total_stats} players with stats")
                return total_stats
            except Exception as e:
                logger.error(f"Fatal error in scrape_recent_games: {e}", exc_info=True)
                await session.rollback()
                raise

    async def _scrape_recent_games(self, session: AsyncSession, days_back: int = 7):
        """Main entry point - scrape rosters first, then recent game stats, and backfill all missing player stats for completed games."""
        effective_days_back = days_back
        last_scrape_date = await self._get_last_stats_scrape_date(session)
        if last_scrape_date:
            today = datetime.now(timezone.utc).date()
            delta_days = (today - last_scrape_date).days
            effective_days_back = max(1, delta_days + 1)  # 1 day padding

        # First, get all team rosters and players (weekly)
        should_scrape_rosters = True
        last_roster_date = await self._get_last_roster_scrape_date(session)
        if last_roster_date:
            today = datetime.now(timezone.utc).date()
            should_scrape_rosters = (today - last_roster_date).days >= 7

        if should_scrape_rosters:
            await self._scrape_teams_and_rosters(session)
            await self._set_last_roster_scrape_date(session, datetime.now(timezone.utc).date())
        else:
            print("Skipping roster scrape (last run within 7 days)")

        # Then scrape recent game stats from boxscores
        print(f"\nScraping game stats from last {effective_days_back} days...")

        total_stats = 0

        for sport_type, league, sport_name in self.SPORTS_CONFIG:
            try:
                game_ids = await self._get_recent_game_ids(session, sport_type, league, effective_days_back)
                print(f"{sport_name}: Found {len(game_ids)} completed games")

                # Process boxscores sequentially to avoid session conflicts
                for game_id in game_ids:
                    try:
                        stats_count = await self._scrape_game_boxscore(
                            session, game_id, sport_type, league, sport_name
                        )
                        total_stats += stats_count
                    except Exception as e:
                        print(f"Error scraping boxscore for game {game_id}: {e}")
                        continue

            except Exception as e:
                print(f"Error scraping {sport_name} game stats: {e}")
                continue

        # --- Backfill: Find all non-upcoming games missing player stats or team stats and fill them ---
        print("\nBackfilling missing player or team stats for all non-upcoming games (any date)...")
        from sqlalchemy import select, or_, and_, not_, exists
        from backend.models.games_results import GameResult
        from backend.models.player_stats import PlayerStats

        # Find all games in games_results with status not 'upcoming' (i.e., include live, final, etc.)
        # and either (no player_stats) OR (home or away team stats_json is null or empty)
        from sqlalchemy import cast, String as SAString
        result = await session.execute(
            select(GameResult).where(
                GameResult.status.isnot(None),
                GameResult.status.notin_(("upcoming", "scheduled", "pre-game", "preseason", "tba", "preview")),
                or_(
                    not_(exists().where(PlayerStats.game_id == GameResult.game_id)),
                    (GameResult.home_team_obj.has(or_(Team.stats_json.is_(None), cast(Team.stats_json, SAString) == '{}'))),
                    (GameResult.away_team_obj.has(or_(Team.stats_json.is_(None), cast(Team.stats_json, SAString) == '{}')))
                )
            )
        )
        missing_games = result.scalars().all()
        print(f"Found {len(missing_games)} non-upcoming games missing player or team stats.")
        # Convert all ORM objects to dicts inside session context
        missing_game_dicts = []
        for game in missing_games:
            game_dict = {
                "game_id": getattr(game, "game_id", None),
                "sport": getattr(game, "sport", None),
                "home_team_id": getattr(game, "home_team_id", None),
                "away_team_id": getattr(game, "away_team_id", None),
                "home_team_name": getattr(game, "home_team_name", None),
                "away_team_name": getattr(game, "away_team_name", None),
                "start_time": getattr(game, "start_time", None),
                "end_time": getattr(game, "end_time", None),
                "venue": getattr(game, "venue", None),
                "home_score": getattr(game, "home_score", None),
                "away_score": getattr(game, "away_score", None),
                "status": getattr(game, "status", None),
                "attendance": getattr(game, "attendance", None),
                "referees": getattr(game, "referees", None),
                "weather": getattr(game, "weather", None),
                "moved_at": getattr(game, "moved_at", None),
            }
            missing_game_dicts.append(game_dict)
        # Now only use dicts outside session context
        # Parallelize with concurrency limit, but each task must use its own session
        import asyncio
        from backend.db import get_session
        semaphore = asyncio.Semaphore(6)  # Limit concurrency to 6 to avoid overloading ESPN/DB

        async def scrape_one(game_dict):
            game_id = game_dict["game_id"]
            game_sport = game_dict["sport"]
            sport_upper = (game_sport or "").upper()
            sport_league_map = {
                "NBA": ("basketball", "nba"),
                "NCAAB": ("basketball", "mens-college-basketball"),
                "NFL": ("football", "nfl"),
                "NCAAF": ("football", "college-football"),
                "NHL": ("hockey", "nhl"),
                "MLB": ("baseball", "mlb"),
                "EPL": ("soccer", "eng.1"),
                "SOCCER": ("soccer", "eng.1"),
            }
            if sport_upper not in sport_league_map:
                print(f"[Backfill] Unknown sport: {game_sport} for game {game_id}, skipping.")
                return 0
            sport_type, league = sport_league_map[sport_upper]
            try:
                async with semaphore:
                    async with get_session() as task_session:
                        stats_count = await self._scrape_game_boxscore(
                            task_session, game_id, sport_type, league, sport_upper
                        )
                        await task_session.commit()
                print(f"[Backfill] Added stats for game {game_id} ({game_sport})")
                return stats_count
            except Exception as e:
                print(f"[Backfill] Error scraping boxscore for game {game_id}: {e}")
                return 0

        # Run all missing games in parallel batches
        results = await asyncio.gather(*(scrape_one(gd) for gd in missing_game_dicts))
        total_stats += sum(results)

        # Only commit and update scrape date for the main session (not per-task sessions)
        await session.commit()
        await self._set_last_stats_scrape_date(session, datetime.now(timezone.utc).date())
        print(f"Game stats scraping complete: {total_stats} stat records (including backfill)")

    async def _get_last_stats_scrape_date(self, session: AsyncSession) -> Optional[date]:
        """Get last successful stats scrape date from scraper_state table"""
        await session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS scraper_state (key TEXT PRIMARY KEY, value TEXT)"
            )
        )
        result = await session.execute(
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

    async def _get_last_roster_scrape_date(self, session: AsyncSession) -> Optional[date]:
        """Get last successful roster scrape date from scraper_state table"""
        await session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS scraper_state (key TEXT PRIMARY KEY, value TEXT)"
            )
        )
        result = await session.execute(
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

    async def _set_last_stats_scrape_date(self, session: AsyncSession, date_value) -> None:
        """Persist last successful stats scrape date"""
        await session.execute(
            text(
                """
                INSERT INTO scraper_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            ),
            {"key": "player_stats_last_scrape", "value": date_value.isoformat()},
        )
        await session.commit()

    async def _set_last_roster_scrape_date(self, session: AsyncSession, date_value) -> None:
        """Persist last successful roster scrape date"""
        await session.execute(
            text(
                """
                INSERT INTO scraper_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            ),
            {"key": "player_rosters_last_scrape", "value": date_value.isoformat()},
        )
        await session.commit()
    
    async def _get_recent_game_ids(self, session: AsyncSession, sport_type: str, league: str, days_back: int) -> List[str]:
        """Get game IDs from recent days - fetches all days concurrently"""
        # Build all API requests upfront
        fetch_tasks = []
        dates = []
        
        for days_ago in range(days_back):
            date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={date}"
            fetch_tasks.append(self.client.get_json(url))
            dates.append(date)
        
        # Fetch all dates concurrently
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        game_ids = []
        
        for date, data in zip(dates, results):
            if isinstance(data, Exception) or not data:
                continue
            
            try:
                events = data.get("events", []) if isinstance(data, dict) else []
                for event in events:
                    status = event.get("status", {}).get("type", {}).get("name", "")
                    # Only process completed games
                    if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                        game_ids.append(event.get("id"))
            except Exception:
                continue
        
        return game_ids
    
    async def _scrape_game_boxscore(
        self, session: AsyncSession, game_id: str, sport_type: str, league: str, sport_name: str
    ) -> int:
        """Scrape boxscore for a single game and save player stats"""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
        import logging
        logger = logging.getLogger(__name__)
        try:
            data = await self.client.get_json(url)
            if not data:
                #logger.error(f"[Boxscore] No data returned for game {game_id}")
                return 0
            if "boxscore" not in data:
                #logger.error(f"[Boxscore] No boxscore found for game {game_id}")
                return 0

            # Upsert final game result (history scraper) and commit to guarantee FK for player_stats
            await self._upsert_game_result(
                session=session,
                data=data,
                game_id=game_id,
                sport_name=sport_name,
                league=league,
            )
            try:
                await session.commit()
            except Exception as commit_e:
                logger.error(f"[Boxscore] Commit failed after upsert_game_result for game {game_id}: {commit_e}", exc_info=True)
                try:
                    await session.rollback()
                except Exception as rollback_e:
                    logger.error(f"[Boxscore] Rollback failed after failed commit for game {game_id}: {rollback_e}", exc_info=True)
                return 0
            result_check = await session.execute(select(GameResult).where(GameResult.game_id == game_id))
            exists = result_check.scalar_one_or_none()
            if not exists:
                return 0
            status_type = (data.get("header", {}).get("competitions", [{}])[0].get("status", {}).get("type", {}) or {})
            status_name = status_type.get("name") or ""
            if status_name not in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                return 0
            boxscore = data["boxscore"]
            stats_added = 0

            is_soccer = sport_type == "soccer"
            try:
                if is_soccer:
                    # ...existing code for soccer...
                    rosters = data.get("rosters", [])
                    for roster in rosters:
                        team_info = roster.get("team", {})
                        team_id = team_info.get("id")
                        players = roster.get("roster", [])
                        for player_entry in players:
                            athlete = player_entry.get("athlete", {})
                            stats = player_entry.get("stats", [])
                            if not athlete or not athlete.get("id"):
                                continue
                            player_id = str(athlete.get("id"))
                            player_name = athlete.get("displayName") or athlete.get("fullName") or "Unknown"
                            try:
                                stat_added = await self._save_player_stats(
                                    session,
                                    game_id=game_id,
                                    player_id=player_id,
                                    player_name=player_name,
                                    team_id=f"{sport_name}-{team_id}" if team_id else None,
                                    sport=sport_name,
                                    league=league,
                                    stats_list=stats,
                                    stat_type="",
                                    stat_labels=[],
                                )
                                if stat_added:
                                    stats_added += 1
                            except Exception as player_e:
                                logger.error(f"[Soccer Boxscore] Error saving stats for player {player_id} ({player_name}) in game {game_id}: {player_e}", exc_info=True)
                                continue
                        # Single commit per team roster
                        try:
                            await session.commit()
                        except Exception as commit_e:
                            logger.error(f"[Soccer Boxscore] Commit failed for game {game_id}: {commit_e}", exc_info=True)
                            await session.rollback()
                else:
                    players_by_team = boxscore.get("players", [])
                    if not players_by_team:
                        logger.warning(f"[Boxscore] No players found in boxscore for game {game_id}")
                    # --- Patch: Aggregate all stat groups per player for all sports ---
                    from collections import defaultdict
                    player_stats_agg = {}
                    player_names = {}
                    player_team_ids = {}
                    for team_players in players_by_team:
                        team_info = team_players.get("team", {})
                        team_id = team_info.get("id")
                        statistics_groups = team_players.get("statistics", [])
                        for stat_group in statistics_groups:
                            stat_type = stat_group.get("name", "")
                            stat_labels = stat_group.get("labels", [])
                            athletes = stat_group.get("athletes", [])
                            if not isinstance(stat_labels, list) or not stat_labels:
                                logger.error(f"[Boxscore] Skipping stat group with missing/malformed stat_labels for team {team_id} in game {game_id}, stat_type={stat_type}: {stat_labels}")
                                continue
                            for athlete_data in athletes:
                                athlete = athlete_data.get("athlete", {})
                                stats = athlete_data.get("stats", [])
                                if not athlete or not athlete.get("id"):
                                    logger.error(f"[Boxscore] Skipping athlete with missing id in game {game_id}, team {team_id}, stat_type {stat_type}")
                                    continue
                                player_id = str(athlete.get("id"))
                                player_name = athlete.get("displayName") or athlete.get("fullName") or "Unknown"
                                if not isinstance(stats, list) or len(stats) == 0:
                                    continue
                                # Aggregate all stat groups for this player
                                if player_id not in player_stats_agg:
                                    player_stats_agg[player_id] = []
                                player_stats_agg[player_id].append((stat_type, stat_labels, stats))
                                player_names[player_id] = player_name
                                player_team_ids[player_id] = f"{sport_name}-{team_id}" if team_id else None
                    # Now, for each player, merge all stat groups and save once
                    for player_id, stat_groups in player_stats_agg.items():
                        merged_stats = {}
                        for stat_type, stat_labels, stats in stat_groups:
                            parsed = self._parse_stats(sport_name, stats, stat_type, stat_labels)
                            merged_stats.update(parsed)
                        try:
                            stat_added = await self._save_player_stats(
                                session,
                                game_id=game_id,
                                player_id=player_id,
                                player_name=player_names[player_id],
                                team_id=player_team_ids[player_id],
                                sport=sport_name,
                                league=league,
                                stats_list=[],
                                stat_type="",
                                stat_labels=[],
                                **merged_stats
                            )
                            if stat_added:
                                stats_added += 1
                        except Exception as player_e:
                            logger.error(f"[Boxscore] Error saving merged stats for player {player_id} ({player_names[player_id]}) in game {game_id}: {player_e}", exc_info=True)
                            continue
                    # Single commit for all players in this game
                    try:
                        await session.commit()
                    except Exception as commit_e:
                        logger.error(f"[Boxscore] Commit failed for game {game_id}: {commit_e}", exc_info=True)
                        await session.rollback()
            except Exception as inner_e:
                logger.error(f"[Boxscore] Error processing player stats for game {game_id}: {inner_e}", exc_info=True)
            return stats_added
        except Exception as e:
            #logger.error(f"[Boxscore] Exception for game {game_id}: {e}", exc_info=True)
            return 0

    async def _upsert_game_result(
        self,
        session: AsyncSession,
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
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return dt.replace(tzinfo=None) if dt.tzinfo else dt
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
                home_team=team_name_for(home),
                away_team=team_name_for(away),
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

            await session.execute(stmt)
        except Exception:
            return
    
    async def _upsert_team(
        self,
        session: AsyncSession,
        team_id: str,
        name: Optional[str],
        abbreviation: Optional[str],
        sport_name: str,
        league: str,
    ) -> bool:
        """Upsert team to database, patching all referencing FKs before changing team_id if needed."""
        from sqlalchemy import update
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Only patch bare numeric FKs if this team has a dash-prefixed id (e.g. NCAAB-228)
            # Skip the UPDATE storm if already normalized to avoid 6 unnecessary queries per team
            if '-' in team_id:
                numeric_id = team_id.split('-', 1)[1]
                # Quick check: does anything still reference the bare numeric id?
                from ..models.games_live import GameLive
                from ..models.games_upcoming import GameUpcoming
                needs_patch = await session.execute(
                    text("SELECT 1 FROM games_results WHERE home_team_id = :nid OR away_team_id = :nid LIMIT 1"),
                    {"nid": numeric_id}
                )
                if needs_patch.first():
                    for col in ["home_team_id", "away_team_id"]:
                        await session.execute(
                            update(GameResult).where(getattr(GameResult, col) == numeric_id).values({col: team_id})
                        )
                        await session.execute(
                            update(GameUpcoming).where(getattr(GameUpcoming, col) == numeric_id).values({col: team_id})
                        )
                        await session.execute(
                            update(GameLive).where(getattr(GameLive, col) == numeric_id).values({col: team_id})
                        )
                    await session.flush()
            stmt = insert(Team).values(
                team_id=team_id,
                name=name,
                abbreviation=abbreviation,
                sport_name=sport_name,
                league=league,
            ).on_conflict_do_nothing(index_elements=["team_id"])
            await session.execute(stmt)
            return True
        except Exception as e:
            logger.error(f"[PlayerStats] Error upserting team {team_id}: {e}")
            return False
    
    async def _upsert_player(
        self,
        session: AsyncSession,
        player_id: str,
        name: Optional[str],
        position: Optional[str],
        team_id: Optional[str],
        sport: str,
        league: str,
        headshot: Optional[str],
        jersey: Optional[str],
    ) -> bool:
        """Upsert player to database (PostgreSQL-optimized)"""
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
            await session.execute(stmt)
            return True
        except Exception as e:
            print(f"Error upserting player {player_id}: {e}")
            return False
    
    async def _save_player_stats(
        self,
        session: AsyncSession,
        game_id: str,
        player_id: str,
        player_name: Optional[str],
        team_id: Optional[str],
        sport: str,
        league: str,
        stats_list: List[str],
        stat_type: str = "",
        stat_labels: Optional[List[str]] = None,
        **extra_stats
    ) -> bool:
        """Parse stats array and save to database"""
        import logging
        logger = logging.getLogger(__name__)
        from sqlalchemy.exc import DBAPIError
        from ..models.player import Player
        from ..models.team import Team
        try:
            from sqlalchemy import update
            # Normalize team_id
            if sport.upper() == "NBA" and team_id and '-' not in str(team_id):
                team_id = f"NBA-{team_id}"

            # Upsert team stub (no SELECT needed - ON CONFLICT handles it)
            if team_id:
                from ..models.team import Team
                team_suffix = team_id.split('-')[-1] if '-' in str(team_id) else str(team_id)
                fallback_name = f"{sport} Team {team_suffix}"
                await session.execute(
                    insert(Team).values(
                        team_id=team_id,
                        name=fallback_name,
                        abbreviation=None,
                        sport_name=sport,
                        league=league,
                    ).on_conflict_do_nothing(index_elements=["team_id"])
                )

            # Upsert player stub (no SELECT needed)
            await session.execute(
                insert(Player).values(
                    player_id=player_id,
                    espn_id=player_id,
                    full_name=player_name,
                    name=player_name,
                    position=None,
                    team_id=team_id,
                    sport=sport,
                    league=league,
                    active=True,
                ).on_conflict_do_nothing(index_elements=["player_id"])
            )

            # Check if stats already exist for this game/player
            from ..models.player_stats import PlayerStats
            result = await session.execute(
                select(PlayerStats).where(
                    PlayerStats.game_id == game_id,
                    PlayerStats.player_id == player_id
                )
            )
            existing = result.scalar_one_or_none()
            # Parse stats based on sport and stat type
            # Use parsed_stats unless extra_stats is provided (for NBA aggregation)
            stats_to_save = extra_stats if extra_stats else self._parse_stats(sport, stats_list, stat_type, stat_labels or [])
            if existing:
                # Update existing record with new stats (merge with existing)
                for key, value in stats_to_save.items():
                    if value is not None:
                        setattr(existing, key, value)
                return True
            else:
                # Always use full normalized team_id (SPORT-##)
                normalized_team_id = team_id
                # If only numeric, patch to SPORT-##
                if team_id and '-' not in str(team_id):
                    sport_map = {'NBA': 'NBA', 'NFL': 'NFL', 'NCAAB': 'NCAAB', 'NCAAF': 'NCAAF', 'NHL': 'NHL', 'EPL': 'EPL', 'SOCCER': 'EPL'}
                    sport_prefix = sport_map.get((sport or '').upper(), (league or '').upper())
                    normalized_team_id = f"{sport_prefix}-{team_id}" if sport_prefix else str(team_id)
                stats_record = PlayerStats(
                    game_id=game_id,
                    player_id=player_id,
                    team_id=normalized_team_id,
                    sport=sport,
                    league=league,
                    **stats_to_save
                )
                session.add(stats_record)
                # Do not commit here; commit should be handled in the parent function for batch efficiency
                return True
        except DBAPIError as e:
            logger.error(f"[PlayerStats] DBAPIError saving stats for player_id={player_id}, game_id={game_id}: {e}", exc_info=True)
            try:
                await session.rollback()
            except Exception as rollback_exc:
                logger.error(f"[PlayerStats] Rollback failed for player_id={player_id}, game_id={game_id}: {rollback_exc}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"[PlayerStats] Exception saving stats for player_id={player_id}, game_id={game_id}: {e}", exc_info=True)
            try:
                await session.rollback()
            except Exception as rollback_exc:
                logger.error(f"[PlayerStats] Rollback failed for player_id={player_id}, game_id={game_id}: {rollback_exc}", exc_info=True)
            return False
    
    def _parse_stats(self, sport: str, stats_list: List[str], stat_type: str = "", stat_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Parse ESPN stats array into database columns"""
        parsed = {}
        stat_labels = stat_labels or []
        
        # Handle soccer stats which come as [{name: ..., value: ...}] format
        if sport == "EPL" and isinstance(stats_list, list) and stats_list and isinstance(stats_list[0], dict):
            # Convert soccer stats dict format to flat dict
            for stat_entry in stats_list:
                if not isinstance(stat_entry, dict):
                    continue
                stat_name = stat_entry.get("name", "").lower()
                stat_value = stat_entry.get("value")
                if stat_value is None or stat_value == "":
                    continue
                # Map soccer stat names to database columns
                if stat_name == "totalgoals":
                    parsed["points"] = self._to_int(stat_value)  # Use 'points' for goals to match display format
                elif stat_name == "goalassists":
                    parsed["assists"] = self._to_int(stat_value)
                elif stat_name == "shotsontarget":
                    parsed["steals"] = self._to_int(stat_value)  # Reuse 'steals' field for shots on target
                elif stat_name == "saves":
                    parsed["blocks"] = self._to_int(stat_value)  # Reuse 'blocks' field for saves
                elif stat_name == "tackles":
                    parsed["turnovers"] = self._to_int(stat_value)  # Reuse 'turnovers' field for tackles
                elif stat_name == "tackles" or stat_name == "tackles":
                    parsed["rebounds"] = self._to_int(stat_value)  # Reuse 'rebounds' field for tackles
                elif stat_name == "yellowcards":
                    parsed["fouls"] = self._to_int(stat_value)
                elif stat_name == "redcards":
                    parsed["fouls"] = (parsed.get("fouls", 0) or 0) + (self._to_int(stat_value) or 0) * 2
                elif stat_name == "appearances":
                    parsed["minutes"] = "1" if stat_value else None  # Just mark as played
                elif stat_name == "totalshots":
                    parsed["fg"] = f"{stat_value}-{stat_value}"
                elif stat_name == "goalsconceded":
                    parsed["turnovers"] = self._to_int(stat_value)  # For goalkeepers, track goals conceded
            return parsed
        
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