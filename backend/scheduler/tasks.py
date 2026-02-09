import asyncio
import logging
from datetime import datetime, UTC

from sqlalchemy import text, select, update, or_
from sqlalchemy.orm import selectinload

from ..services.scraper_nba import NBAScraper
from ..services.scraper_nfl import NFLScraper
from ..services.scraper_nhl import NHLScraper
from ..services.scraper_mlb import MLBScraper
from ..services.scraper_ufc import UFCScraper
from ..services.scraper_stats import PlayerStatsScraper
from ..services.espn_client import ESPNClient
from ..services.betting.engine import BettingEngine
from ..services.alerts.manager import AlertManager
from ..services.aai.fresh_data_scraper import FreshDataScraper
from .write_queue import DatabaseWriteQueue


logger = logging.getLogger(__name__)

SPORTS_CONFIG = [
    ("basketball", "nba", "NBA"),
    ("basketball", "mens-college-basketball", "NCAAB"),
    ("football", "nfl", "NFL"),
    ("hockey", "nhl", "NHL"),
    ("soccer", "eng.1", "EPL"),
]


class Scheduler:
    """
    Background scheduler for sports betting data.
    
    Scraping Schedule:
    ------------------
    Every 60 seconds:
        - Live game scores and status updates
        - Game status changes (move finals to games_results)
        - Bet grading for completed games
        - Game live alerts
    
    Every 2 hours:
        - Full game data for all sports (NBA, NFL, NHL, MLB, UFC, NCAAB, EPL)
        - Fresh injury reports for all teams playing today
        - Weather forecasts for outdoor games
        - Player stats for last 7 days of games
    
    Data Sources:
    -------------
    - ESPN Scoreboard API (games, scores, schedules)
    - ESPN v2 API (injuries with nested athlete details)
    - Open-Meteo API (weather forecasts, no API key needed)
    - ESPN Stats API (player performance data)
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.client = ESPNClient()
        self.alerts = AlertManager(session_factory=session_factory)
        self.write_queue = DatabaseWriteQueue()  # Queue for all database writes
        self.game_status_tracker = {}  # Track game statuses to detect when they go live

        self.scrapers = [
            NBAScraper(self.client),
            NFLScraper(self.client),
            NHLScraper(self.client),
            MLBScraper(self.client),
            UFCScraper(self.client),
        ]
    
    async def start(self):
        """Start all background workers"""
        await self.alerts.queue.start_worker()
        await self.write_queue.start_worker()
    
    async def stop(self):
        """Stop all background workers"""
        await self.alerts.queue.stop_worker()
        # Wait for write queue to empty before stopping
        await self.write_queue.wait_empty(timeout=5.0)
        await self.write_queue.stop_worker()

    async def run_scrapers(self):
        """Queue the scraper operations"""
        self.write_queue.enqueue(
            "run_scrapers",
            self._execute_scrapers
        )
    
    async def _execute_scrapers(self):
        """Execute game scrapers, injuries, weather, and player stats (queued operation)"""
        print("🚀 Starting comprehensive scrape cycle...")
        
        # Step 1: Run game scrapers
        for scraper in self.scrapers:
            try:
                await scraper.scrape()
            except Exception as e:
                await self.alerts.create(
                    severity="error",
                    category="scraper",
                    message=f"Scraper failed: {scraper.__class__.__name__}",
                    metadata=str(e),
                )
        
        # Step 2: Scrape fresh injuries and weather for today's games
        try:
            async with self.session_factory() as session:
                fresh_scraper = FreshDataScraper(session)
                try:
                    # Scrape games (to get ESPN IDs)
                    print("  📅 Fetching today's games...")
                    games_count = await fresh_scraper._scrape_todays_games()
                    
                    # Scrape injuries using the ESPN IDs we just collected
                    print("  🏥 Fetching injuries...")
                    injuries_count = await fresh_scraper._scrape_injuries()
                    
                    # Update weather forecasts
                    print("  🌦️ Updating weather forecasts...")
                    weather_count = await fresh_scraper._update_weather()
                    
                    print(f"  ✅ Scrape complete: {games_count} games, {injuries_count} injuries, {weather_count} weather forecasts")
                finally:
                    await fresh_scraper.close()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"Fresh data scraper failed: {e}")
            await self.alerts.create(
                severity="error",
                category="scraper",
                message="Fresh data scraper failed",
                metadata=tb,
            )
        
        # Step 3: Run player stats scraper (scrape last 7 days of games)
        try:
            async with self.session_factory() as session:
                stats_scraper = PlayerStatsScraper(self.client, session)
                await stats_scraper.scrape_recent_games(days_back=7)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"Player stats scraper failed: {e}")
            await self.alerts.create(
                severity="error",
                category="scraper",
                message="Player stats scraper failed",
                metadata=tb,
            )
    
    async def cleanup(self):
        """Close client sessions"""
        await self.client.close()

    async def update_live_games(self):
        """Fetch today's games from ESPN and queue database updates"""
        try:
            from datetime import datetime as dt, timedelta
            from zoneinfo import ZoneInfo
            
            game_data = []
            
            # Use PST dates for ESPN scoreboard queries
            now_pst = dt.now(ZoneInfo("America/Los_Angeles"))
            today_pst = now_pst.strftime("%Y%m%d")
            yesterday_pst = (now_pst - timedelta(days=1)).strftime("%Y%m%d")

            allowed_statuses = {
                "STATUS_IN_PROGRESS",
                "STATUS_HALFTIME",
                "STATUS_FIRST_HALF",
                "STATUS_SECOND_HALF",
                "STATUS_EXTRA_TIME",
                "STATUS_PENALTIES",
                "STATUS_BREAK",
                "STATUS_SCHEDULED",
                "STATUS_FINAL",
                "STATUS_COMPLETE",
                "STATUS_FULL_TIME",
                "STATUS_END",
                "STATUS_DELAYED",
                "STATUS_POSTPONED",
                "STATUS_CANCELED",
                "STATUS_SUSPENDED",
                "STATUS_ABANDONED",
            }

            def should_include(status_type: str, status_detail: str, finals_only: bool) -> bool:
                if finals_only:
                    return self._is_final_status(status_type) or self._is_final_status(status_detail)
                if status_type in allowed_statuses:
                    return True
                # Soccer live minutes like "68'"
                if status_detail and "'" in status_detail:
                    return True
                return False
            
            for sport_type, league, sport_name in SPORTS_CONFIG:
                # Fetch today's games (PST) and include live/upcoming/final
                today_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={today_pst}"
                today_data = await self.client.get_json(today_url)

                # Fetch yesterday's games (PST) and include finals only
                yesterday_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={yesterday_pst}"
                yesterday_data = await self.client.get_json(yesterday_url)

                for data, finals_only in [(today_data, False), (yesterday_data, True)]:
                    if not data:
                        continue

                    events = data.get("events", [])
                    for event in events:
                        game_id = event.get("id")
                        status_type = event.get("status", {}).get("type", {}).get("name", "")
                        status_detail = event.get("status", {}).get("type", {}).get("detail", "")
                        
                        if not should_include(status_type, status_detail, finals_only):
                            continue
                    
                        competitions = event.get("competitions", [])
                        
                        if not competitions:
                            continue
                        
                        comp = competitions[0]
                        competitors = comp.get("competitors", [])
                        
                        home_team = next((c for c in competitors if c.get("homeAway") == "home"), None)
                        away_team = next((c for c in competitors if c.get("homeAway") == "away"), None)
                        
                        if not home_team or not away_team:
                            continue
                        
                        home_team_name = home_team.get("team", {}).get("displayName", "Unknown")
                        away_team_name = away_team.get("team", {}).get("displayName", "Unknown")
                        home_score = int(home_team.get("score", 0))
                        away_score = int(away_team.get("score", 0))
                        
                        # Get start time
                        start_time = event.get("date", "")
                        
                        # Get period and clock for live games
                        status = event.get("status", {})
                        period = status.get("period")
                        clock = status.get("displayClock", "")
                        
                        # Check if game just went live (today only)
                        if not finals_only:
                            previous_status = self.game_status_tracker.get(game_id)
                            is_now_live = (status_type in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]) and (
                                previous_status not in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]
                            )
                            
                            # Update status tracker
                            self.game_status_tracker[game_id] = status_type
                            
                            # Queue alert if game just went live
                            if is_now_live:
                                import json
                                await self.alerts.create(
                                    severity="info",
                                    category="game_live",
                                    message=f"{away_team_name} @ {home_team_name} is now LIVE",
                                    metadata=json.dumps({
                                        "game_id": game_id,
                                        "home_team": home_team_name,
                                        "away_team": away_team_name,
                                        "home_score": home_score,
                                        "away_score": away_score,
                                        "sport": sport_name,
                                        "status": status_detail,
                                        "period": period,
                                        "clock": clock
                                    })
                                )
                        
                        game_data.append({
                            "game_id": game_id,
                            "home_team_name": home_team_name,
                            "away_team_name": away_team_name,
                            "home_score": home_score,
                            "away_score": away_score,
                            "period": period,
                            "clock": clock,
                            "sport": sport_name,
                            "league": league,
                            "status": status_detail,
                            "status_type": status_type,
                            "start_time": start_time,
                            "updated_at_new": datetime.now(UTC)
                        })
            
            # Queue the database write operation
            if game_data:
                self.write_queue.enqueue(
                    "update_live_games",
                    self._write_live_games,
                    game_data
                )
            
        except Exception as e:
            print(f"Live games update failed: {e}")
            await self.alerts.create(
                severity="error",
                category="scraper",
                message="Live games update failed",
                metadata=str(e),
            )
    
    async def _write_live_games(self, game_data: list):
        """Write live games to database (queued operation)"""
        try:
            async with self.session_factory() as session:
                # Purge only stale rows from previous days to keep today's games visible
                await session.execute(text("""
                    DELETE FROM games_live
                    WHERE DATE(updated_at_new) < DATE('now')
                """))
                
                # Upsert new games
                for game in game_data:
                    # First, upsert into main games table
                    await session.execute(text("""
                        INSERT INTO games (game_id, sport, league, start_time, status, 
                                         home_team_name, away_team_name, home_score, away_score, 
                                         period, clock)
                        VALUES (:game_id, :sport, :league, :start_time, :status, 
                                :home_team_name, :away_team_name, :home_score, :away_score, 
                                :period, :clock)
                        ON CONFLICT(game_id) DO UPDATE SET
                            sport = excluded.sport,
                            league = excluded.league,
                            start_time = excluded.start_time,
                            status = excluded.status,
                            home_team_name = excluded.home_team_name,
                            away_team_name = excluded.away_team_name,
                            home_score = excluded.home_score,
                            away_score = excluded.away_score,
                            period = excluded.period,
                            clock = excluded.clock
                    """), game)
                    
                    # Then upsert into games_live snapshot table
                    await session.execute(text("""
                        INSERT INTO games_live (game_id, home_team_name, away_team_name, home_score, 
                                               away_score, period, clock, sport, status, updated_at_new)
                        VALUES (:game_id, :home_team_name, :away_team_name, :home_score, :away_score, 
                                :period, :clock, :sport, :status, :updated_at_new)
                        ON CONFLICT(game_id) DO UPDATE SET
                            home_team_name = excluded.home_team_name,
                            away_team_name = excluded.away_team_name,
                            home_score = excluded.home_score,
                            away_score = excluded.away_score,
                            period = excluded.period,
                            clock = excluded.clock,
                            sport = excluded.sport,
                            status = excluded.status,
                            updated_at_new = excluded.updated_at_new
                    """), game)

                    status_type = (game.get("status_type") or "").upper()
                    if "FINAL" not in status_type:
                        await session.execute(text("""
                            INSERT INTO games_upcoming (game_id, sport, league, start_time, status,
                                                       home_team, away_team, scraped_at)
                            VALUES (:game_id, :sport, :league, :start_time, :status,
                                    :home_team_name, :away_team_name, :updated_at_new)
                            ON CONFLICT(game_id) DO UPDATE SET
                                sport = excluded.sport,
                                league = excluded.league,
                                start_time = excluded.start_time,
                                status = excluded.status,
                                home_team = excluded.home_team,
                                away_team = excluded.away_team,
                                scraped_at = excluded.scraped_at
                        """), game)
                
                await session.commit()
        except Exception as e:
            logger.exception("Failed to write live games: %s", e)
            raise

    async def grade_bets(self):
        """Queue bet grading operation"""
        self.write_queue.enqueue(
            "grade_bets",
            self._grade_bets
        )

    async def update_game_statuses(self):
        """Queue game status update operation"""
        self.write_queue.enqueue(
            "update_game_statuses",
            self._update_game_statuses
        )
    
    async def _update_game_statuses(self):
        """Update game statuses from ESPN and write finished games to games_results"""
        async with self.session_factory() as session:
            from ..models.game import Game
            from ..models.games_results import GameResult
            from ..models.bet import Bet
            from ..repositories.sport_repo import SportRepository
            from sqlalchemy.orm import selectinload
            
            try:
                # Get all non-final games
                games = await session.execute(
                    select(Game)
                    .options(selectinload(Game.sport_rel))
                    .where(
                        or_(
                            ~Game.status.ilike("%final%"),
                            Game.sport_id.is_(None),
                            Game.sport.is_(None),
                            Game.league.is_(None),
                        )
                    )
                )
                scheduled_games = games.scalars().all()
                logger.info("[Status Update] Found %s non-final games to check", len(scheduled_games))
                
                updated_count = 0
                sport_repo = SportRepository(session)
                for game in scheduled_games:
                    # Get sport from a bet that references this game
                    bet_result = await session.execute(
                        select(Bet).options(selectinload(Bet.sport)).where(Bet.game_id == game.game_id).limit(1)
                    )
                    bet = bet_result.scalar_one_or_none()
                    
                    sport_name = None
                    if bet and bet.sport and bet.sport.name:
                        sport_name = bet.sport.name
                    elif game.sport:
                        sport_name = game.sport
                    elif game.sport_rel and getattr(game.sport_rel, "name", None):
                        sport_name = game.sport_rel.name

                    # Build a prioritized search list. If sport is unknown or wrong, fall back to all sports.
                    search_sports = []
                    if sport_name:
                        sport_type, league = self._get_sport_league(sport_name)
                        if sport_type:
                            search_sports.append((sport_type, league, sport_name))
                        else:
                            logger.debug("[Status Update] Unknown sport '%s' for game %s, falling back", sport_name, game.game_id)

                    # Always include full fallback list (excluding duplicates)
                    for sport_type, league, sport_label in SPORTS_CONFIG:
                        if (sport_type, league, sport_label) not in search_sports:
                            search_sports.append((sport_type, league, sport_label))

                    event = None
                    resolved_sport = None
                    resolved_league = None

                    # Try scoreboard + summary for the primary sport first
                    sport_type, league, sport_label = search_sports[0]
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard"
                    data = await self.client.get_json(url)

                    if data and "events" in data:
                        event = next((e for e in data["events"] if e.get("id") == str(game.game_id)), None)
                        if event:
                            resolved_sport = sport_label
                            resolved_league = league

                    # If not in scoreboard, fall back to event summary by ID (handles past games)
                    if not event:
                        summary_url = (
                            f"https://site.api.espn.com/apis/site/v2/sports/"
                            f"{sport_type}/{league}/summary?event={game.game_id}"
                        )
                        summary = await self.client.get_json(summary_url)
                        if summary:
                            comp = None
                            if summary.get("header", {}).get("competitions"):
                                comp = summary["header"]["competitions"][0]
                            elif summary.get("competitions"):
                                comp = summary["competitions"][0]
                            if comp:
                                event = {"competitions": [comp]}
                                resolved_sport = sport_label
                                resolved_league = league

                    # If still not found, scan other sports by event ID
                    if not event and len(search_sports) > 1:
                        for alt_sport_type, alt_league, alt_label in search_sports[1:]:
                            summary_url = (
                                f"https://site.api.espn.com/apis/site/v2/sports/"
                                f"{alt_sport_type}/{alt_league}/summary?event={game.game_id}"
                            )
                            summary = await self.client.get_json(summary_url)
                            if not summary:
                                continue
                            comp = None
                            if summary.get("header", {}).get("competitions"):
                                comp = summary["header"]["competitions"][0]
                            elif summary.get("competitions"):
                                comp = summary["competitions"][0]
                            if comp:
                                event = {"competitions": [comp]}
                                resolved_sport = alt_label
                                resolved_league = alt_league
                                break

                    if not event:
                        logger.debug("[Status Update] Game %s not found in ESPN for any sport", game.game_id)
                        continue

                    # Persist resolved sport/league for future lookups
                    if resolved_sport and resolved_sport != game.sport:
                        game.sport = resolved_sport
                    if resolved_league and hasattr(game, "league"):
                        game.league = resolved_league

                    # Correct sport_id on game and related bets when ESPN sport resolves differently
                    if resolved_league:
                        resolved_sport_row = await sport_repo.get_by_league_code(resolved_league)
                    else:
                        resolved_sport_row = await sport_repo.get_by_league_code((resolved_sport or "").lower())

                    if resolved_sport_row:
                        if getattr(game, "sport_id", None) != resolved_sport_row.id:
                            game.sport_id = resolved_sport_row.id
                        await session.execute(
                            update(Bet)
                            .where(Bet.game_id.in_([game.game_id, str(game.game_id)]))
                            .values(sport_id=resolved_sport_row.id)
                        )

                    if event:
                        comp = event.get("competitions", [{}])[0]
                        status = comp.get("status", {}).get("type", {}).get("name", "scheduled")

                        logger.debug("[Status Update] Game %s: %s -> %s", game.game_id, game.status, status)

                        # Update game status - the game object is already tracked by the session
                        game.status = status
                        updated_count += 1

                        # If game is final, write to games_results
                        if self._is_final_status(status):
                            teams = comp.get("competitors", [])
                            home = next((t for t in teams if t.get("homeAway") == "home"), None)
                            away = next((t for t in teams if t.get("homeAway") == "away"), None)

                            if home and away:
                                # Check if already in games_results
                                result = await session.execute(
                                    select(GameResult).where(GameResult.game_id == game.game_id)
                                )
                                existing = result.scalar_one_or_none()

                                if not existing:
                                    game_result = GameResult(
                                        game_id=game.game_id,
                                        sport=sport_name,
                                        start_time=game.start_time,
                                        status=status,
                                        home_team_id=home.get("id"),
                                        home_team_name=home.get("team", {}).get("displayName"),
                                        away_team_id=away.get("id"),
                                        away_team_name=away.get("team", {}).get("displayName"),
                                        home_score=home.get("score"),
                                        away_score=away.get("score"),
                                        venue=comp.get("venue", {}).get("name") if comp.get("venue") else None,
                                    )
                                    session.add(game_result)
                                    logger.debug(
                                        "[Status Update] Created GameResult for %s: %s vs %s",
                                        game.game_id,
                                        away.get("team", {}).get("displayName"),
                                        home.get("team", {}).get("displayName"),
                                    )
                                else:
                                    # Update existing result
                                    existing.status = status
                                    existing.home_score = home.get("score")
                                    existing.away_score = away.get("score")
                                    logger.debug("[Status Update] Updated GameResult for %s", game.game_id)
                
                logger.info("[Status Update] Updated %s games", updated_count)
                # Backfill/correct bet sport_id based on games table
                await session.execute(
                    text(
                        """
                        UPDATE bets
                        SET sport_id = (
                            SELECT sport_id FROM games WHERE games.game_id = bets.game_id
                        )
                        WHERE (
                            sport_id IS NULL
                            OR sport_id != (
                                SELECT sport_id FROM games WHERE games.game_id = bets.game_id
                            )
                        )
                        AND (
                            SELECT sport_id FROM games WHERE games.game_id = bets.game_id
                        ) IS NOT NULL
                        """
                    )
                )
                await session.commit()
            except Exception as e:
                logger.exception("[Status Update] Error: %s", e)
                import traceback
                traceback.print_exc()
    
    def _get_sport_league(self, sport: str) -> tuple:
        """Map sport name to ESPN API path"""
        if not sport:
            return (None, None)
        sport_map = {
            "NBA": ("basketball", "nba"),
            "NCAAB": ("basketball", "mens-college-basketball"),
            "NFL": ("football", "nfl"),
            "NHL": ("hockey", "nhl"),
            "EPL": ("soccer", "eng.1"),
            "SOCCER": ("soccer", "eng.1"),
            "ENG.1": ("soccer", "eng.1"),
        }
        return sport_map.get(sport.upper(), (None, None))
    
    def _is_final_status(self, status: str) -> bool:
        """Check if game status is final"""
        if not status:
            return False
        status_lower = status.lower()
        return "final" in status_lower or status in ("STATUS_FINAL", "STATUS_FULL_TIME")

    async def _grade_bets(self):
        """Grade all pending bets (queued operation)"""
        async with self.session_factory() as session:
            engine = BettingEngine(session)
            await engine.grade_all_pending()

    async def loop(self):
        while True:
            await self.update_live_games()
            await self.run_scrapers()
            await self.update_game_statuses()  # Update finished games
            await self.grade_bets()
            await asyncio.sleep(60)