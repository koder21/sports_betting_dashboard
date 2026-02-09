from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.aai.recommendations import AAIBetRecommender
from ..services.aai.pre_bet_verifier import PreBetVerifier
from ..services.aai.fresh_data_scraper import FreshDataScraper

router = APIRouter()


@router.get("/refresh-and-calculate")
async def refresh_and_calculate(
    models: str = Query(default="all"),
    session: AsyncSession = Depends(get_session),
):
    """
    🚀 COMPREHENSIVE FRESH DATA PIPELINE
    
    Step 1: Scrape ALL fresh data
      - Today's games from ESPN (all sports)
      - Injuries for all teams playing today
      - Weather forecasts for outdoor games
      - Game odds and status updates
    
    Step 2: Calculate AI recommendations
      - Blend form-based confidence with external models
      - Apply injury impact adjustments
      - Apply weather impact adjustments
      - Generate optimized singles and parlays
    
    Returns: Full AAI recommendations with fresh data summary
    """
    scrape_summary = {"success": False, "message": "Skipped"}
    
    # Step 1: Scrape fresh data (with generous timeout for complete data)
    scraper = FreshDataScraper(session)
    try:
        # Set a 3 minute timeout for complete scraping
        import asyncio
        scrape_summary = await asyncio.wait_for(
            scraper.scrape_all_fresh_data(),
            timeout=180.0  # 3 minutes - enough time for all injuries
        )
    except asyncio.TimeoutError:
        scrape_summary = {
            "success": False,
            "message": "⚠️ Scrape timeout (3min) - using partial data",
            "games_updated": 0,
            "injuries_updated": 0,
            "weather_forecasts": 0,
            "elapsed_seconds": 180.0
        }
        print("⚠️ Fresh data scrape timed out after 3 minutes")
    except Exception as e:
        scrape_summary = {
            "success": False,
            "message": f"⚠️ Scrape error: {str(e)[:100]}",
            "games_updated": 0,
            "injuries_updated": 0,
            "weather_forecasts": 0,
            "elapsed_seconds": 0
        }
        print(f"❌ Fresh data scrape failed: {e}")
    finally:
        await scraper.close()
    
    # Step 2: Calculate recommendations (ALWAYS run, even if scraping failed)
    recommender = AAIBetRecommender(session)
    selected = {m.strip().lower() for m in models.split(",") if m.strip()}
    recommendations = await recommender.generate(external_models=selected)
    
    # Combine results
    return {
        **recommendations,
        "fresh_data": scrape_summary,
        "data_freshness": "LIVE" if scrape_summary.get("success") else "CACHED",
    }


@router.get("/recommendations")
async def get_recommendations(
    models: str = Query(default="all"),
    session: AsyncSession = Depends(get_session),
):
    svc = AAIBetRecommender(session)
    selected = {m.strip().lower() for m in models.split(",") if m.strip()}
    return await svc.generate(external_models=selected)


@router.get("/verify-before-bet/{game_id}")
async def verify_before_bet(
    game_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Comprehensive pre-bet verification - fetches FRESH data before placing real money.
    
    Checks:
    - Game status (not postponed/cancelled)
    - Latest injuries from ESPN
    - Weather forecast for game time
    - Current odds
    - Lineup changes
    
    Returns detailed verification report with recommendations.
    """
    verifier = PreBetVerifier(session)
    try:
        result = await verifier.verify_game(game_id)
        return result
    finally:
        await verifier.close()
