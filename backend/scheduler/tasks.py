import asyncio
import logging
from datetime import datetime, UTC

from sqlalchemy import text, select
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
        """Execute game scrapers and player stats scraper (queued operation)"""
        # Run game scrapers
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
        
        # Run player stats scraper (scrape last 7 days of games)
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
                            "status": status_detail,
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
            from sqlalchemy.orm import selectinload
            
            try:
                # Get all non-final games
                games = await session.execute(
                    select(Game)
                    .options(selectinload(Game.sport_rel))
                    .where(~Game.status.like("%Final%"))
                )
                scheduled_games = games.scalars().all()
                logger.info("[Status Update] Found %s non-final games to check", len(scheduled_games))
                
                updated_count = 0
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

                    if not sport_name:
                        logger.debug("[Status Update] Skipping game %s: no sport available", game.game_id)
                        continue
                    
                    # Fetch latest data from ESPN
                    sport_type, league = self._get_sport_league(sport_name)
                    if not sport_type:
                        logger.debug("[Status Update] Skipping game %s: unknown sport: %s", game.game_id, sport_name)
                        continue
                        
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard"
                    data = await self.client.get_json(url)
                    
                    if not data or "events" not in data:
                        continue
                    
                    # Find matching game
                    for event in data["events"]:
                        if event.get("id") == game.game_id:
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
                            
                            break
                
                logger.info("[Status Update] Updated %s games", updated_count)
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