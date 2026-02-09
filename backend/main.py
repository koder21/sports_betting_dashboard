from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime, timedelta

from .config import settings
from .db import init_db, AsyncSessionLocal
from .routers import health, games, props, bets, alerts, analytics, live, scraping, sports_analytics, aai_bets, leaderboards, bet_placement
from .scheduler.tasks import Scheduler

app = FastAPI(title="Sports Intelligence Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
    
    # Create scheduler instance early so queue worker can be started
    scheduler_instance = Scheduler(AsyncSessionLocal)
    await scheduler_instance.start()  # Start alert queue worker
    
    # Wait 5 minutes before starting scrapes to avoid bog-down at startup
    print("Scheduler: Waiting 2 minutes before starting scrapes...")
    await asyncio.sleep(120)  # 5 minutes
    
    # Run full scrape after delay
    try:
        print("Running full scrape (5 min after startup)...")
        await scheduler_instance.run_scrapers()
        last_full_scrape = datetime.now()
        print("Full scrape completed successfully")
    except Exception as e:
        print(f"Full scrape error: {e}")
        import traceback
        traceback.print_exc()
    
    while True:
        try:
            if scheduler_instance is None:
                scheduler_instance = Scheduler(AsyncSessionLocal)
                await scheduler_instance.start()
            
            # Update live games every cycle (60s)
            await scheduler_instance.update_live_games()
            await scheduler_instance.update_game_statuses()  # Update finished games to games_results
            await scheduler_instance.grade_bets()
            
            # Full scrape every 2 hours
            if last_full_scrape is None or datetime.now() - last_full_scrape >= timedelta(hours=2):
                print("Running scheduled full scrape (2 hour interval)...")
                await scheduler_instance.run_scrapers()
                last_full_scrape = datetime.now()
            
            await asyncio.sleep(60)  # Update every 60 seconds
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(60)


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