"""FastAPI application entry point with background scheduler."""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db import init_db, AsyncSessionLocal
from backend.routers import (
    health, games, props, bets, alerts, analytics, live, scraping,
    sports_analytics, aai_bets, leaderboards, bet_placement, bets_pending
)
from backend.scheduler.tasks import Scheduler


# Enhanced logging: log to both console and debug.log file
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# File handler (debug.log)
file_handler = logging.FileHandler('debug.log', mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

# Scheduler configuration constants
STARTUP_DELAY_SECONDS = 30  # Wait before first scrape
LIVE_UPDATE_INTERVAL_SECONDS = 60
MAIN_UPDATE_INTERVAL_SECONDS = 1800  # 30 minutes
SCRAPE_INTERVAL_MINUTES = 30
BACKFILL_INTERVAL_MINUTES = 30


app = FastAPI(title="Sports Intelligence Platform", version="1.0.0")

# When CORS_ORIGINS is not set, allow all origins without credentials (safe default for initial deploy)
_cors_origins = [str(o) for o in settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler_task = None
_scheduler_instance = None

class SchedulerManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.scheduler = None
        self.last_full_scrape = None
        self.last_backfill = None
    
    async def ensure_scheduler(self) -> Scheduler:
        if self.scheduler is None:
            logger.warning("Scheduler instance lost, recreating...")
            self.scheduler = Scheduler(self.session_factory)
            await self.scheduler.start()
        return self.scheduler
    
    async def update_live_games_loop(self):
        while True:
            try:
                scheduler = await self.ensure_scheduler()
                await scheduler.update_live_games()
            except asyncio.CancelledError:
                logger.info("Live games loop cancelled")
                break
            except Exception as e:
                logger.error("Live games update error: %s", e, exc_info=True)
            await asyncio.sleep(LIVE_UPDATE_INTERVAL_SECONDS)
    
    async def main_update_loop(self):
        scrape_interval = timedelta(minutes=SCRAPE_INTERVAL_MINUTES)
        backfill_interval = timedelta(minutes=BACKFILL_INTERVAL_MINUTES)
        
        while True:
            try:
                scheduler = await self.ensure_scheduler()
                now = datetime.now()
                
                if self.last_full_scrape is None or (now - self.last_full_scrape) >= scrape_interval:
                    logger.info("Running scheduled full scrape (%d min interval)...", SCRAPE_INTERVAL_MINUTES)
                    await scheduler.run_scrapers()
                    self.last_full_scrape = now
                
                if self.last_backfill is None or (now - self.last_backfill) >= backfill_interval:
                    logger.info("Running scheduled player stats backfill (%d min interval)...", BACKFILL_INTERVAL_MINUTES)
                    await scheduler.backfill_player_stats()
                    self.last_backfill = now
                
                await scheduler.update_game_statuses()
                await scheduler.grade_bets()
                
            except asyncio.CancelledError:
                logger.info("Main update loop cancelled")
                break
            except Exception as e:
                logger.error("Main update loop error: %s", e, exc_info=True)
            
            await asyncio.sleep(MAIN_UPDATE_INTERVAL_SECONDS)
    
    async def run(self):
        logger.info("Scheduler: Waiting %d seconds before starting...", STARTUP_DELAY_SECONDS)
        await asyncio.sleep(STARTUP_DELAY_SECONDS)        
        await asyncio.gather(
            self.update_live_games_loop(),
            self.main_update_loop(),
            return_exceptions=False
        )
    
    async def stop(self):
        if self.scheduler:
            try:
                await self.scheduler.stop()
                await self.scheduler.cleanup()
            except Exception as e:
                logger.error("Error during scheduler cleanup: %s", e)
            finally:
                self.scheduler = None

@app.on_event("startup")
async def on_startup() -> None:
    global _scheduler_task, _scheduler_instance

    # Retry DB connection — Railway Postgres may take a few seconds to be ready
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            await init_db()
            logger.info("Database initialized: %s", settings.DATABASE_URL)
            break
        except Exception as e:
            if attempt == max_retries:
                logger.error("Could not connect to database after %d attempts: %s", max_retries, e)
                raise
            logger.warning("DB connection attempt %d/%d failed: %s — retrying in 3s", attempt, max_retries, e)
            await asyncio.sleep(3)

    _scheduler_instance = SchedulerManager(AsyncSessionLocal)
    _scheduler_task = asyncio.create_task(_scheduler_instance.run())
    logger.info("Background scheduler started")

@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _scheduler_task, _scheduler_instance
    
    if _scheduler_instance:
        await _scheduler_instance.stop()
    
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Application shutdown complete")

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(props.router, prefix="/api/props", tags=["props"])
app.include_router(bets.router, prefix="/api/bets", tags=["bets"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(sports_analytics.router, prefix="/api/sports-analytics", tags=["sports-analytics"])
app.include_router(aai_bets.router, prefix="/api/aai-bets", tags=["aai-bets"])
app.include_router(bet_placement.router, prefix="/bets")
app.include_router(bets_pending.router, prefix="/api/bets", tags=["bets"])
app.include_router(live.router, prefix="/api/live", tags=["live"])
app.include_router(leaderboards.router, prefix="/api/leaderboards", tags=["leaderboards"])
app.include_router(scraping.router, prefix="/api/scrape", tags=["scrape"])