import logging
import sys
import time
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from dateutil import parser
from sqlalchemy import text, select
from ..services.unified_sport_scraper import (
    NBAScraper,
    MLBScraper,
    NHLScraper,
    NFLScraper,
)
from ..services.scraper_stats import PlayerStatsScraper
from ..services.espn_client import ESPNClient
from ..services.alerts.manager import AlertManager
from ..services.aai.fresh_data_scraper import FreshDataScraper
from .write_queue import DatabaseWriteQueue
from backend.models.games_results import GameResult


# --- LOGGING CONFIGURATION ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler for persistent logs
file_handler = logging.FileHandler("backend.log", mode="a")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
file_handler.setFormatter(file_formatter)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)

# Stream handler for stdout (optional, keeps logs in terminal too)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.WARNING)
stream_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)
stream_handler.setFormatter(stream_formatter)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(stream_handler)


# (Print redirection removed; use logger.info/debug/warning/error directly for all output)

SPORTS_CONFIG = [
    ("basketball", "nba", "NBA"),
    ("basketball", "mens-college-basketball", "NCAAB"),
    ("football", "nfl", "NFL"),
    ("football", "college-football", "NCAAF"),
    ("hockey", "nhl", "NHL"),
    ("soccer", "eng.1", "EPL"),
    ("baseball", "mlb", "MLB"),
]


# ...existing code...
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
    - Full game data for all sports (NBA, NFL, NHL, MLB, NCAAB, EPL)
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


def log_duration(operation_name):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"[METRICS] {operation_name} duration: {duration:.2f} seconds")
            return result

        return wrapper

    return decorator


class Scheduler:
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
        ]

    async def periodic_backup_check(self):
        """Check every 30 minutes if a backup is needed, and run it if so."""
        while True:
            try:
                # If backup logic is needed, implement here
                pass
            except Exception as e:
                logger.error(f"Backup check failed: {e}")
            await asyncio.sleep(1800)  # 30 minutes

    async def start(self):
        """Start all background workers and periodic backup check"""
        await self.alerts.queue.start_worker()
        await self.write_queue.start_worker()
        asyncio.create_task(self.periodic_backup_check())

    async def stop(self):
        """Stop all background workers"""
        await self.alerts.queue.stop_worker()
        # Wait for write queue to empty before stopping
        await self.write_queue.wait_empty(timeout=5.0)
        await self.write_queue.stop_worker()

    async def run_scrapers(self):
        """Queue the scraper operations"""
        self.write_queue.enqueue("run_scrapers", self._execute_scrapers)

    @log_duration("_execute_scrapers")
    async def _execute_scrapers(self):
        """Execute game scrapers, injuries, weather, and player stats (queued operation)"""
        print("🚀 Starting comprehensive scrape cycle...")

        # OPTIMIZATION: Run game scrapers concurrently instead of sequentially (5x speedup potential)
        async def run_scraper(scraper):
            try:
                await scraper.scrape()
            except Exception as e:
                # Only await if AlertManager.create is actually async (session provided)
                await self.alerts.create(
                    severity="error",
                    category="scraper",
                    message=f"Scraper failed: {scraper.__class__.__name__}",
                    metadata=str(e),
                )

        # Run all scrapers concurrently
        await asyncio.gather(
            *[run_scraper(scraper) for scraper in self.scrapers], return_exceptions=True
        )

        # Step 2: Scrape fresh injuries and weather for today's games (concurrent with scrapers above)
        try:
            async with self.session_factory() as session:
                fresh_scraper = FreshDataScraper(session)
                try:
                    # OPTIMIZATION: Run fresh scraper operations concurrently (3x speedup)
                    # Run sequentially - these share a session and cannot run concurrently
                    logger.info("Fetching today's games...")
                    games_count = await fresh_scraper._scrape_todays_games()
                    injuries_count = await fresh_scraper._scrape_injuries()
                    await fresh_scraper.session.commit()  # commit after injuries
                    weather_count = await fresh_scraper._update_weather()

                    logger.info(
                        f"Scrape complete: {games_count} games, {injuries_count} injuries, {weather_count} weather forecasts"
                    )
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
            # Always re-scrape and upsert player stats for all completed games in the last N days
            HOURS = 168  # 7 days * 24 hours
            async with self.session_factory() as session:
                stats_scraper = PlayerStatsScraper(self.client)
                # ...existing code...
                cutoff = datetime.utcnow() - timedelta(hours=HOURS)
                result = await session.execute(
                    select(GameResult).where(
                        GameResult.status.isnot(None),
                        GameResult.status.notin_(
                            [
                                "upcoming",
                                "scheduled",
                                "pre-game",
                                "preseason",
                                "tba",
                                "preview",
                            ]
                        ),
                        GameResult.start_time >= cutoff,
                    )
                )
                recent_games = result.scalars().all()
                for game in recent_games:
                    sport_upper = (game.sport or "").upper()
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
                        continue
                    sport_type, league = sport_league_map[sport_upper]
                    try:
                        # Use a fresh session per game to avoid greenlet/async context errors
                        async with self.session_factory() as stats_session:
                            await stats_scraper._scrape_game_boxscore(
                                stats_session,
                                game.game_id,
                                sport_type,
                                league,
                                sport_upper,
                            )
                            await stats_session.commit()
                    except Exception as scrape_e:
                        # ...existing code...
                        tb_scrape = traceback.format_exc()
                        logger.error(
                            f"Auto-scraper failed for game {game.game_id}: {scrape_e}\n{tb_scrape}"
                        )
                        continue
        except Exception as e:
            # ...existing code...
            tb = traceback.format_exc()
            print(f"Player stats auto-scraper failed: {e}")
            await self.alerts.create(
                severity="error",
                category="scraper",
                message="Player stats auto-scraper failed",
                metadata=tb,
            )

    async def cleanup(self):
        """Close client sessions"""
        await self.client.close()

    @log_duration("update_live_games")
    async def update_live_games(self, direct_write: bool = False):
        """Fetch today's games from ESPN and queue database updates.

        When direct_write=True the DB write is awaited directly instead of being
        handed to the background write-queue worker.  Use this for on-demand
        (non-scheduled) calls where stopping the worker immediately after would
        race against the enqueued task.
        """
        try:
            from zoneinfo import ZoneInfo

            game_data = []

            # Use PST dates for ESPN scoreboard queries
            now_pst = datetime.now(ZoneInfo("America/Los_Angeles"))
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

            def should_include(
                status_type: str, status_detail: str, finals_only: bool
            ) -> bool:
                if finals_only:
                    return self._is_final_status(status_type) or self._is_final_status(
                        status_detail
                    )
                if status_type in allowed_statuses:
                    return True
                # Soccer live minutes like "68'"
                if status_detail and "'" in status_detail:
                    return True
                return False

            for sport_type, league, sport_name in SPORTS_CONFIG:
                # OPTIMIZATION: Fetch today's and yesterday's games concurrently (2x speedup per sport)
                today_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={today_pst}"
                yesterday_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={yesterday_pst}"

                today_data, yesterday_data = await asyncio.gather(
                    self.client.get_json(today_url),
                    self.client.get_json(yesterday_url),
                    return_exceptions=False,
                )

                for data, finals_only in [(today_data, False), (yesterday_data, True)]:
                    if not data:
                        continue

                    events = data.get("events", [])
                    for event in events:
                        game_id = event.get("id")
                        status_type = (
                            event.get("status", {}).get("type", {}).get("name", "")
                        )
                        status_detail = (
                            event.get("status", {}).get("type", {}).get("detail", "")
                        )

                        if not should_include(status_type, status_detail, finals_only):
                            continue

                        competitions = event.get("competitions", [])

                        if not competitions:
                            continue

                        comp = competitions[0]
                        competitors = comp.get("competitors", [])

                        home_team = next(
                            (c for c in competitors if c.get("homeAway") == "home"),
                            None,
                        )
                        away_team = next(
                            (c for c in competitors if c.get("homeAway") == "away"),
                            None,
                        )

                        if not home_team or not away_team:
                            continue

                        home_team_name = home_team.get("team", {}).get(
                            "displayName", "Unknown"
                        )
                        away_team_name = away_team.get("team", {}).get(
                            "displayName", "Unknown"
                        )
                        home_score = (
                            int(home_team.get("score", 0))
                            if home_team.get("score", 0) is not None
                            else None
                        )
                        away_score = (
                            int(away_team.get("score", 0))
                            if away_team.get("score", 0) is not None
                            else None
                        )

                        # Get start time
                        start_time = event.get("date", "")

                        # Get period and clock for live games
                        status = event.get("status", {})
                        period = status.get("period")
                        clock = status.get("displayClock", "")

                        # Check if game just went live (today only)
                        if not finals_only:
                            previous_status = self.game_status_tracker.get(game_id)
                            is_now_live = (
                                status_type in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]
                            ) and (
                                previous_status
                                not in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]
                            )

                            # Update status tracker
                            self.game_status_tracker[game_id] = status_type

                            # Queue alert if game just went live
                            if is_now_live:
                                # ...existing code...
                                try:
                                    coro = self.alerts.create(
                                        severity="info",
                                        category="game_live",
                                        message=f"{away_team_name} @ {home_team_name} is now LIVE",
                                        metadata=json.dumps(
                                            {
                                                "game_id": game_id,
                                                "home_team_name": home_team_name,
                                                "away_team_name": away_team_name,
                                                "home_score": home_score,
                                                "away_score": away_score,
                                                "sport": sport_name,
                                                "status": status_detail,
                                                "period": period,
                                                "clock": clock,
                                            }
                                        ),
                                    )
                                    if asyncio.iscoroutine(coro):
                                        await coro
                                except Exception as alert_err:
                                    logger.warning(
                                        f"[Alert] Failed to create live-game alert: {alert_err}"
                                    )

                        # Parse start_time to datetime if it's a string
                        parsed_start_time = start_time
                        if isinstance(start_time, str):
                            try:
                                parsed_start_time = parser.isoparse(start_time)
                            except Exception:
                                parsed_start_time = None
                        # --- SPORT/LEAGUE NORMALIZATION ---
                        normalized_sport = sport_name.lower() if sport_name else None
                        normalized_league = league
                        if normalized_sport == "ncaab":
                            normalized_league = "ncaab"
                        game_data.append(
                            {
                                "game_id": game_id,
                                "home_team_name": home_team_name,
                                "away_team_name": away_team_name,
                                "home_score": int(home_score)
                                if home_score is not None
                                else None,
                                "away_score": int(away_score)
                                if away_score is not None
                                else None,
                                "period": period,
                                "clock": clock,
                                "sport": normalized_sport,
                                "league": normalized_league,
                                "status": status_detail,
                                "status_type": status_type,
                                "start_time": parsed_start_time,
                                "updated_at": datetime.now(timezone.utc),
                            }
                        )

            # Write game data — directly when called on-demand, queued when scheduled
            if game_data:
                if direct_write:
                    await self._write_live_games(game_data)
                else:
                    self.write_queue.enqueue(
                        "update_live_games", self._write_live_games, game_data
                    )

        except Exception as e:
            print(f"Live games update failed: {e}")
            # asyncio is already imported globally
            await self.alerts.create(
                severity="error",
                category="scraper",
                message="Live games update failed",
                metadata=str(e),
            )

    @log_duration("_write_live_games")
    async def _write_live_games(self, game_data: list):
        """Write live games to database (queued operation)"""
        try:
            async with self.session_factory() as session:
                # Purge only stale rows from previous days to keep today's games visible
                await session.execute(
                    text("""
                    DELETE FROM games_live
                    WHERE updated_at::date < CURRENT_DATE
                """)
                )

                # Upsert new games
                for game in game_data:
                    # --- Type enforcement for scores, period, clock, and datetimes ---
                    for score_key in ("home_score", "away_score"):
                        val = game.get(score_key)
                        if val is not None and not isinstance(val, int):
                            try:
                                game[score_key] = int(val)
                            except Exception:
                                game[score_key] = None
                    # Ensure period and clock are always strings
                    for str_key in ("period", "clock"):
                        val = game.get(str_key)
                        if val is not None and not isinstance(val, str):
                            game[str_key] = str(val)
                    # Ensure start_time and updated_at are naive datetimes
                    for dt_key in ("start_time", "updated_at"):
                        dt_val = game.get(dt_key)
                        if dt_val is not None and hasattr(dt_val, "replace"):
                            # Remove tzinfo if present
                            game[dt_key] = dt_val.replace(tzinfo=None)

                    # First, upsert into main games table
                    # --- SPORT/LEAGUE NORMALIZATION FOR UPSERT ---
                    if game.get("sport") == "ncaab":
                        game["league"] = "ncaab"
                    if game.get("sport"):
                        game["sport"] = game["sport"].lower()
                    await session.execute(
                        text("""
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
                    """),
                        game,
                    )
                    # Then upsert into games_live snapshot table
                    # --- SPORT/LEAGUE NORMALIZATION FOR UPSERT ---
                    if game.get("sport") == "ncaab":
                        game["league"] = "ncaab"
                    if game.get("sport"):
                        game["sport"] = game["sport"].lower()
                    await session.execute(
                        text("""
                        INSERT INTO games_live (game_id, home_team_name, away_team_name, home_score, 
                                               away_score, period, clock, sport, status, updated_at)
                        VALUES (:game_id, :home_team_name, :away_team_name, :home_score, :away_score, 
                                :period, :clock, :sport, :status, :updated_at)
                        ON CONFLICT(game_id) DO UPDATE SET
                            home_team_name = excluded.home_team_name,
                            away_team_name = excluded.away_team_name,
                            home_score = excluded.home_score,
                            away_score = excluded.away_score,
                            period = excluded.period,
                            clock = excluded.clock,
                            sport = excluded.sport,
                            status = excluded.status,
                            updated_at = excluded.updated_at
                    """),
                        game,
                    )
                    status_type = (game.get("status_type") or "").upper()
                    if "FINAL" not in status_type:
                        # --- SPORT/LEAGUE NORMALIZATION FOR UPSERT ---
                        if game.get("sport") == "ncaab":
                            game["league"] = "ncaab"
                        if game.get("sport"):
                            game["sport"] = game["sport"].lower()
                        await session.execute(
                            text("""
                            INSERT INTO games_upcoming (game_id, sport, league, start_time, status,
                                           home_team_name, away_team_name, scraped_at)
                            VALUES (:game_id, :sport, :league, :start_time, :status,
                                :home_team_name, :away_team_name, :updated_at)
                            ON CONFLICT(game_id) DO UPDATE SET
                            sport = excluded.sport,
                            league = excluded.league,
                            start_time = excluded.start_time,
                            status = excluded.status,
                            home_team_name = excluded.home_team_name,
                            away_team_name = excluded.away_team_name,
                            scraped_at = excluded.scraped_at
                        """),
                            game,
                        )

                await session.commit()
        except Exception as e:
            logger.exception("Failed to write live games: %s", e)
            raise

    @log_duration("grade_bets")
    async def grade_bets(self):
        """Grade pending bets against completed games."""
        try:
            async with self.session_factory() as session:
                from backend.models.bet import Bet
                from backend.models.alert import Alert

                # Get all pending bets
                stmt = select(Bet).where(Bet.status == "pending")
                result = await session.execute(stmt)
                pending_bets = result.scalars().all()

                if not pending_bets:
                    return

                logger.info(f"Grading {len(pending_bets)} pending bets...")
                graded_count = 0

                from backend.services.betting.grader import BetGrader

                grader = BetGrader(session)
                for bet in pending_bets:
                    result = await grader.grade(bet)
                    if result:
                        # Only grade if result is not None (game/player stats finalized)
                        bet.status = result.get("status", bet.status)
                        bet.profit = result.get("profit", bet.profit)
                        bet.result_time = datetime.now(timezone.utc)
                        # Create alert
                        pick = bet.selection or bet.raw_text or ""
                        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        alert = Alert(
                            created_at=created_at,
                            severity="info" if bet.status == "won" else "warning",
                            category="bet_result",
                            message=f"Bet {'Won' if bet.status == 'won' else 'Lost'}: {pick} | {getattr(bet, 'away_team', '')} @ {getattr(bet, 'home_team', '')}",
                            meta=str(
                                {
                                    "bet_id": bet.id,
                                    "profit": float(bet.profit)
                                    if bet.profit is not None
                                    else 0.0,
                                    "stake": float(bet.stake)
                                    if bet.stake is not None
                                    else 0.0,
                                }
                            ),
                            acknowledged=False,
                        )
                        session.add(alert)
                        graded_count += 1
                await grader.close()

                if graded_count > 0:
                    await session.commit()  # ✅ Commit once at end
                    logger.info(f"✅ Graded {graded_count} bets")

        except Exception as e:
            logger.error(f"✗ grade_bets failed: {e}", exc_info=True)

    def _check_bet_outcome(self, bet, game_result):
        """Check if bet won based on game result."""
        # ...existing code...
        # Use bet.selection for pick string
        pick = bet.selection or bet.raw_text or ""
        if "ML" in pick or "Moneyline" in pick:
            if pick.startswith(game_result.home_team_name):
                return game_result.home_score > game_result.away_score
            else:
                return game_result.away_score > game_result.home_score
        elif "spread" in pick.lower() or any(c in pick for c in ["+", "-"]):
            spread_match = re.search(r"([+-]?\d+\.?\d*)", pick)
            if spread_match:
                spread = float(spread_match.group(1))
                home_score = game_result.home_score
                away_score = game_result.away_score
                if pick.startswith(game_result.home_team_name):
                    return (home_score + spread) > away_score
                else:
                    return (away_score + spread) > home_score
        elif "over" in pick.lower() or "under" in pick.lower():
            total = game_result.home_score + game_result.away_score
            total_match = re.search(r"(\d+\.?\d*)", pick)
            if total_match:
                line = float(total_match.group(1))
                if "over" in pick.lower():
                    return total > line
                else:
                    return total < line
        # Default: couldn't parse, mark as lost
        logger = logging.getLogger(__name__)
        logger.warning(f"Couldn't parse bet type for: {pick}")
        return False

    async def backfill_player_stats(self):
        """Backfill missing player stats for completed games (queued operation)"""
        self.write_queue.enqueue(
            "backfill_player_stats", self._execute_backfill_player_stats
        )

    @log_duration("_execute_backfill_player_stats")
    async def _execute_backfill_player_stats(self):
        """Execute backfill of missing player stats using robust lookup (games or games_results) and scraping logic identical to manual refresh."""
        try:
            # Find all completed games in games_results with no player_stats
            from sqlalchemy import select, not_, exists
            from backend.models.player_stats import PlayerStats
            from backend.models.game import Game
            from backend.models.games_live import GameLive
            from backend.models.games_upcoming import GameUpcoming

            async with self.session_factory() as session:
                result = await session.execute(
                    select(GameResult).where(
                        not_(exists().where(PlayerStats.game_id == GameResult.game_id))
                    )
                )
                missing_game_ids = [g.game_id for g in result.scalars().all()]
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
                stats_scraper = PlayerStatsScraper(self.client)
                for gid in missing_game_ids:
                    # Try to find the game in any table
                    game = None
                    for model in [Game, GameResult, GameLive, GameUpcoming]:
                        result = await session.execute(
                            select(model).where(model.game_id == gid)
                        )
                        game = result.scalar()
                        if game:
                            break
                    if not game or not getattr(game, "sport", None):
                        logger.warning(
                            f"[Backfill] Could not find sport for game {gid}, skipping."
                        )
                        continue
                    sport_upper = (game.sport or "").upper()
                    if sport_upper not in sport_league_map:
                        logger.warning(
                            f"[Backfill] Unknown sport: {game.sport} for game {gid}, skipping."
                        )
                        continue
                    sport_type, league = sport_league_map[sport_upper]
                    # --- Ensure the game exists in games_results before scraping player stats ---
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    from backend.services.espn_client import ESPNClient

                    client = ESPNClient()
                    # Only check direct columns, not relationships, to avoid async context errors
                    required_fields = [
                        "sport",
                        "league",
                        "start_time",
                        "home_team_id",
                        "away_team_id",
                        "home_team_name",
                        "away_team_name",
                        "status",
                    ]  # for games_results
                    missing = False
                    for f in required_fields:
                        value = getattr(game, f, None)
                        if value is None:
                            missing = True
                            break
                    if missing:
                        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={gid}"
                        summary = await client.get_json(summary_url)
                        competitions = (
                            summary.get("competitions", [{}])[0] if summary else {}
                        )
                        home_team = competitions.get("home", {}).get("team", {})
                        away_team = competitions.get("away", {}).get("team", {})
                        start_time = competitions.get("date")
                        status = (
                            competitions.get("status", {}).get("type", {}).get("name")
                        )
                        league_val = competitions.get("league", {}).get(
                            "abbreviation", league
                        )
                        # Upsert teams table with latest ESPN data
                        from backend.models.team import Team

                        for team_data in [home_team, away_team]:
                            if team_data and team_data.get("id"):
                                await session.execute(
                                    pg_insert(Team)
                                    .values(
                                        team_id=f"NBA-{team_data.get('id')}",
                                        name=team_data.get("displayName"),
                                        abbreviation=team_data.get("abbreviation"),
                                        logo=team_data.get("logo"),
                                        sport_name=sport_upper,
                                        league=league_val,
                                    )
                                    .on_conflict_do_nothing(index_elements=["team_id"])
                                )
                        # Upsert games table with latest team IDs/names
                        from backend.models.game import Game

                        await session.execute(
                            pg_insert(Game)
                            .values(
                                game_id=gid,
                                sport=game.sport or sport_upper,
                                league=league_val,
                                start_time=start_time,
                                home_team_id=f"NBA-{home_team.get('id')}"
                                if home_team.get("id")
                                else None,
                                away_team_id=f"NBA-{away_team.get('id')}"
                                if away_team.get("id")
                                else None,
                                home_team_name=home_team.get("displayName"),
                                away_team_name=away_team.get("displayName"),
                                status=status,
                            )
                            .on_conflict_do_update(
                                index_elements=["game_id"],
                                set_={
                                    "sport": game.sport or sport_upper,
                                    "league": league_val,
                                    "start_time": start_time,
                                    "home_team_id": f"NBA-{home_team.get('id')}"
                                    if home_team.get("id")
                                    else None,
                                    "away_team_id": f"NBA-{away_team.get('id')}"
                                    if away_team.get("id")
                                    else None,
                                    "home_team_name": home_team.get("displayName"),
                                    "away_team_name": away_team.get("displayName"),
                                    "status": status,
                                },
                            )
                        )
                        # Upsert games_results as before
                        games_results_upsert_dict = {
                            "game_id": gid,
                            "sport": game.sport or sport_upper,
                            "league": league_val,
                            "start_time": start_time,
                            "home_team_id": f"NBA-{home_team.get('id')}"
                            if home_team.get("id")
                            else None,
                            "away_team_id": f"NBA-{away_team.get('id')}"
                            if away_team.get("id")
                            else None,
                            "home_team": home_team.get(
                                "displayName"
                            ),  # actual DB column
                            "away_team": away_team.get(
                                "displayName"
                            ),  # actual DB column
                            "status": status,
                        }
                        # logger.debug(f"[DEBUG] games_results_upsert_dict: {games_results_upsert_dict}")
                        stmt = pg_insert(GameResult).values(**games_results_upsert_dict)
                        update_dict = games_results_upsert_dict.copy()
                        update_dict.pop("game_id", None)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["game_id"], set_=update_dict
                        )
                        await session.execute(stmt)
                        try:
                            await session.commit()
                        except Exception as commit_e:
                            logger.error(
                                f"[Backfill] Commit failed after upsert_game_result for game {gid}: {commit_e}",
                                exc_info=True,
                            )
                            await session.rollback()
                            continue
                    else:
                        games_results_upsert_dict = {
                            "game_id": gid,
                            "sport": game.sport,
                            "league": getattr(game, "league", None),
                            "start_time": getattr(game, "start_time", None),
                            "home_team_id": getattr(game, "home_team_id", None),
                            "away_team_id": getattr(game, "away_team_id", None),
                            # Use home_team_name and away_team_name columns, not relationships
                            "home_team": getattr(
                                game, "home_team_name", None
                            ),  # actual DB column
                            "away_team": getattr(
                                game, "away_team_name", None
                            ),  # actual DB column
                            "status": getattr(game, "status", None),
                        }
                        # logger.debug(f"[DEBUG] games_results_upsert_dict (no conflict): {games_results_upsert_dict}")
                        await session.execute(
                            pg_insert(GameResult)
                            .values(**games_results_upsert_dict)
                            .on_conflict_do_nothing(index_elements=["game_id"])
                        )
                        try:
                            await session.commit()
                        except Exception as commit_e:
                            logger.error(
                                f"[Backfill] Commit failed after upsert_game_result for game {gid}: {commit_e}",
                                exc_info=True,
                            )
                            await session.rollback()
                            continue
                    try:
                        # Always re-scrape and upsert player stats, even if stats already exist for this game
                        if hasattr(stats_scraper, "_scrape_game_boxscore"):
                            await stats_scraper._scrape_game_boxscore(
                                session, gid, sport_type, league, sport_upper
                            )
                        else:
                            logger.error(
                                f"[Backfill] PlayerStatsScraper missing _scrape_game_boxscore method for game {gid}"
                            )
                        await session.commit()
                    except Exception as e:
                        if "greenlet_spawn" in str(
                            e
                        ) or "can't call await_only()" in str(e):
                            logger.error(
                                f"[Backfill] Async context error for game {gid}: {e}. Skipping."
                            )
                            continue
                        logger.error(f"[Backfill] Error scraping game {gid}: {e}")
                    finally:
                        if hasattr(client, "close"):
                            await client.close()
        except Exception as e:
            logger.error(f"[Backfill] Error during backfill: {e}", exc_info=True)
            # asyncio is already imported globally
            await self.alerts.create(
                severity="warning",
                category="backfill",
                message="Player stats backfill encountered an error",
                metadata=str(e),
            )

    def _is_final_status(self, status: str) -> bool:
        """Check if game status is final/finished for any sport"""
        if not status:
            return False
        status_lower = status.lower()
        finished_keywords = [
            "final",
            "full-time",
            "ft",
            "final overtime",
            "final/ot",
            "final ot",
            "status_final",
            "status_full_time",
            "status_ft",
            "status_final overtime",
            "status_final/ot",
            "status_final ot",
        ]
        return any(k in status_lower for k in finished_keywords)

    @log_duration("update_game_statuses")
    async def update_game_statuses(self):
        """Update game statuses from ESPN and write finished games to games_results (queued operation)"""
        try:
            from sqlalchemy import select
            from backend.models.games_live import GameLive
            from backend.models.games_results import GameResult
            from backend.models.game import Game

            async with self.session_factory() as session:
                # Get all live games
                live_query = await session.execute(select(GameLive))
                live_games = live_query.scalars().all()
                # Get all games_results
                results_query = await session.execute(select(GameResult))
                results_games = results_query.scalars().all()
                result_ids = {r.game_id for r in results_games}
                # Find games that are final in GameLive but not in GameResult
                final_games = []
                for live in live_games:
                    status_detail = live.status or ""
                    if (
                        self._is_final_status(status_detail)
                        and live.game_id not in result_ids
                    ):
                        final_games.append(live)
                # Move final games to games_results
                for live in final_games:
                    # Get start_time from Game table
                    game_q = await session.execute(
                        select(Game).where(Game.game_id == live.game_id)
                    )
                    game = game_q.scalar()
                    start_time = game.start_time if game else None
                    game_result = GameResult(
                        game_id=live.game_id,
                        sport=live.sport,
                        league=game.league if game else None,
                        start_time=start_time,
                        status=live.status,
                        home_team_id=getattr(live, "home_team_id", None),
                        home_team_name=live.home_team_name,
                        away_team_id=getattr(live, "away_team_id", None),
                        away_team_name=live.away_team_name,
                        home_score=live.home_score,
                        away_score=live.away_score,
                    )
                    session.add(game_result)
                if final_games:
                    await session.commit()
                    logger.info(
                        f"Moved {len(final_games)} final games to games_results."
                    )
            # Restore auto-grading: grade bets after moving finals
            await self.grade_bets()
        except Exception as e:
            logger.error(f"Failed to update game statuses: {e}", exc_info=True)

    @log_duration("backfill_last_7_days")
    async def backfill_last_7_days(self):
        """Fetch and insert game records for the last 7 days for all sports."""
        from zoneinfo import ZoneInfo
        from datetime import timedelta

        now_pst = datetime.now(ZoneInfo("America/Los_Angeles"))
        for days_ago in range(0, 7):  # 0 to 6 inclusive (today and last 6 days)
            date = now_pst - timedelta(days=days_ago)
            date_str = date.strftime("%Y%m%d")
            for sport_type, league, sport_name in SPORTS_CONFIG:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={date_str}"
                data = await self.client.get_json(url)
                if not data:
                    continue
                events = data.get("events", [])
                game_data = []
                for event in events:
                    game_id = event.get("id")
                    status_type = (
                        event.get("status", {}).get("type", {}).get("name", "")
                    )
                    status_detail = (
                        event.get("status", {}).get("type", {}).get("detail", "")
                    )
                    competitions = event.get("competitions", [])
                    if not competitions:
                        continue
                    comp = competitions[0]
                    competitors = comp.get("competitors", [])
                    home_team = next(
                        (c for c in competitors if c.get("homeAway") == "home"), None
                    )
                    away_team = next(
                        (c for c in competitors if c.get("homeAway") == "away"), None
                    )
                    if not home_team or not away_team:
                        continue
                    home_team_name = home_team.get("team", {}).get(
                        "displayName", "Unknown"
                    )
                    away_team_name = away_team.get("team", {}).get(
                        "displayName", "Unknown"
                    )
                    home_score = (
                        int(home_team.get("score", 0))
                        if home_team.get("score", 0) is not None
                        else None
                    )
                    away_score = (
                        int(away_team.get("score", 0))
                        if away_team.get("score", 0) is not None
                        else None
                    )
                    start_time = event.get("date", "")
                    period = event.get("status", {}).get("period", "")
                    clock = event.get("status", {}).get("displayClock", "")
                    # Parse start_time
                    parsed_start_time = None
                    if isinstance(start_time, str):
                        try:
                            parsed_start_time = parser.isoparse(start_time)
                        except Exception:
                            parsed_start_time = None
                    normalized_sport = sport_name.lower() if sport_name else None
                    normalized_league = league
                    if normalized_sport == "ncaab":
                        normalized_league = "ncaab"
                    game_data.append(
                        {
                            "game_id": game_id,
                            "home_team_name": home_team_name,
                            "away_team_name": away_team_name,
                            "home_score": home_score,
                            "away_score": away_score,
                            "period": period,
                            "clock": clock,
                            "sport": normalized_sport,
                            "league": normalized_league,
                            "status": status_detail,
                            "status_type": status_type,
                            "start_time": parsed_start_time,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    )
                if game_data:
                    # Write the game data using the same _write_live_games method (which upserts to games, games_live, games_upcoming)
                    await self._write_live_games(game_data)
