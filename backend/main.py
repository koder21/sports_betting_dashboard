from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime, timedelta

from .config import settings
from .db import init_db, AsyncSessionLocal
from .routers import health, games, props, bets, alerts, analytics, live, scraping, sports_analytics, aai_bets, leaderboards, bet_placement
from .scheduler.tasks import Scheduler

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sports Intelligence Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler_task = None
scheduler_instance = None  # Track the scheduler instance for cleanup


async def scheduler_worker():
    """Worker task that manages background scheduling"""
    global scheduler_instance
    last_full_scrape = None
    last_backfill = None
    scrape_interval = timedelta(hours=2)
    backfill_interval = timedelta(hours=1)
    update_cycle = 60  # seconds
    startup_delay = 120  # seconds before first scrape
    
    # Create scheduler instance early so queue worker can be started
    scheduler_instance = Scheduler(AsyncSessionLocal)
    await scheduler_instance.start()  # Start alert queue worker
    
    # Wait before starting scrapes to avoid startup congestion
    logger.info("Scheduler: Waiting %d seconds before starting scrapes...", startup_delay)
    await asyncio.sleep(startup_delay)
    
    # Run full scrape after delay
    try:
        logger.info("Running initial full scrape after startup...")
        await scheduler_instance.run_scrapers()
        last_full_scrape = datetime.now()
        logger.info("Full scrape completed successfully")
    except Exception as e:
        logger.error("Initial full scrape error: %s", e, exc_info=True)
    
    # Run backfill after startup
    try:
        logger.info("Running initial player stats backfill after startup...")
        await scheduler_instance.backfill_player_stats()
        last_backfill = datetime.now()
        logger.info("Backfill initiated successfully")
    except Exception as e:
        logger.error("Initial backfill error: %s", e, exc_info=True)
    
    while True:
        try:
            # Safety check: ensure scheduler still exists
            if scheduler_instance is None:
                logger.warning("Scheduler instance lost, recreating...")
                scheduler_instance = Scheduler(AsyncSessionLocal)
                await scheduler_instance.start()
                continue
            
            # Update live games every cycle (60s) - run concurrently for efficiency
            await asyncio.gather(
                scheduler_instance.update_live_games(),
                scheduler_instance.update_game_statuses(),
                scheduler_instance.grade_bets(),
                return_exceptions=True
            )
            
            # Full scrape every 2 hours
            now = datetime.now()
            if last_full_scrape is None or (now - last_full_scrape) >= scrape_interval:
                logger.info("Running scheduled full scrape (2 hour interval)...")
                await scheduler_instance.run_scrapers()
                last_full_scrape = now
            
            # Player stats backfill every 1 hour
            if last_backfill is None or (now - last_backfill) >= backfill_interval:
                logger.info("Running scheduled player stats backfill (hourly)...")
                await scheduler_instance.backfill_player_stats()
                last_backfill = now
            
            await asyncio.sleep(update_cycle)
        except asyncio.CancelledError:
            logger.info("Scheduler worker cancelled, shutting down...")
            break
        except Exception as e:
            logger.error("Scheduler error: %s", e, exc_info=True)
            await asyncio.sleep(update_cycle)


@app.on_event("startup")
async def on_startup() -> None:
    global scheduler_task
    await init_db()
    
    # Start the scheduler in the background
    scheduler_task = asyncio.create_task(scheduler_worker())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global scheduler_task, scheduler_instance
    
    # Stop alert queue worker first
    if scheduler_instance:
        try:
            await scheduler_instance.stop()
        except Exception as e:
            print(f"Error stopping alert queue: {e}")
    
    # Cancel the scheduler task
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Close the ESPNClient session
    if scheduler_instance:
        try:
            await scheduler_instance.cleanup()
        except Exception as e:
            print(f"Error during scheduler cleanup: {e}")


app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(games.router, prefix="/games", tags=["games"])
app.include_router(props.router, prefix="/props", tags=["props"])
app.include_router(bets.router, prefix="/bets", tags=["bets"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(sports_analytics.router, prefix="/sports-analytics", tags=["sports-analytics"])
app.include_router(aai_bets.router, prefix="/aai-bets", tags=["aai-bets"])
app.include_router(bet_placement.router, tags=["bet-placement"])
app.include_router(live.router, prefix="/live", tags=["live"])
app.include_router(leaderboards.router, prefix="/leaderboards", tags=["leaderboards"])
app.include_router(scraping.router, tags=["scrape"])