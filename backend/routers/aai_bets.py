"""
AAI Bets API Routes
===================
Endpoints for AI-powered betting recommendations.

Endpoints:
- GET /refresh-and-calculate - Scrape fresh data + generate recommendations
- GET /recommendations - Get recommendations (uses cached data)
- GET /verify-before-bet/{game_id} - Verify specific game before betting
"""
import asyncio
import logging
from typing import Optional, Set, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.aai.fresh_data_scraper import FreshDataScraper
from ..services.aai.pre_bet_verifier import PreBetVerifier
from ..services.betting import RecommendationsEngine  # ← NEW: Modern betting engine
from backend.utils.redis_cache import redis_cache
from ..services.scraper_stats import ESPNClient, PlayerStatsScraper

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
SCRAPE_TIMEOUT = 180  # 3 minutes
STATS_SCRAPE_TIMEOUT = 180
DEFAULT_BANKROLL = 1000


@router.get("/refresh-and-calculate")
@redis_cache(ttl=60)
async def refresh_and_calculate(
    models: str = Query(default="all", description="Comma-separated model list (e.g., 'elo,vegas,ml')"),
    min_confidence: float = Query(default=60, ge=0, le=100, description="Minimum confidence threshold"),
    sports: Optional[str] = Query(default=None, description="Comma-separated sports (e.g., 'NBA,NFL')"),
    bankroll: float = Query(default=DEFAULT_BANKROLL, gt=0, description="Bankroll for Kelly sizing"),
    session: AsyncSession = Depends(get_db),
):
    """
    **Complete fresh data pipeline + AI recommendations.**
    
    Steps:
    1. Scrape fresh games, injuries, weather
    2. Scrape recent completed games for stats
    3. Generate AI betting recommendations
    
    Query Parameters:
    - models: Model selection (default: "all")
    - min_confidence: Min confidence % (default: 60)
    - sports: Filter by sports (default: all)
    - bankroll: Your bankroll for bet sizing (default: $1000)
    
    Returns:
    - singles: Single bet recommendations
    - parlays: Parlay recommendations
    - summary: Statistics and metadata
    - fresh_data: Scraping summary
    - data_freshness: "LIVE" or "CACHED"
    """
    scrape_summary = {"success": False, "message": "Pending"}
    
    # Step 1: Scrape fresh upcoming games data (games, injuries, weather)
    logger.info("Starting fresh data scrape...")
    scraper = FreshDataScraper(session)
    try:
        scrape_summary = await asyncio.wait_for(
            scraper.scrape_all_fresh_data(),
            timeout=SCRAPE_TIMEOUT
        )
        logger.info(f"Fresh data scrape completed: {scrape_summary.get('message')}")
    except asyncio.TimeoutError:
        scrape_summary = {
            "success": False,
            "message": f"⚠️ Scrape timeout ({SCRAPE_TIMEOUT}s) - using partial data",
            "games_updated": 0,
            "injuries_updated": 0,
            "weather_forecasts": 0,
            "elapsed_seconds": SCRAPE_TIMEOUT
        }
        logger.warning("Fresh data scrape timed out")
    except Exception as e:
        scrape_summary = {
            "success": False,
            "message": f"⚠️ Scrape error: {str(e)[:100]}",
            "games_updated": 0,
            "injuries_updated": 0,
            "weather_forecasts": 0,
            "elapsed_seconds": 0,
            "error": str(e)
        }
        logger.error(f"Fresh data scrape failed: {e}", exc_info=True)
    finally:
        await scraper.close()

    # Step 2: Scrape completed games for historical stats
    logger.info("Scraping recent completed games...")
    client = ESPNClient()
    stats_scraper = PlayerStatsScraper(client)
    stats_summary: Dict[str, Any] = {"success": False, "games_scraped": 0}
    
    try:
        await asyncio.wait_for(
            stats_scraper.scrape_recent_games(days_back=7),
            timeout=STATS_SCRAPE_TIMEOUT
        )
        stats_summary = {"success": True, "games_scraped": 7}
        logger.info("Recent games scraped successfully")
    except asyncio.TimeoutError:
        logger.warning("Stats scrape timed out")
        stats_summary = {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Completed games scrape failed: {e}", exc_info=True)
        stats_summary = {"success": False, "error": str(e)[:100]}
    finally:
        await stats_scraper.close()
        await client.close()

    # Step 3: Generate AI recommendations using new engine
    logger.info("Generating AI recommendations...")
    try:
        engine = RecommendationsEngine(session, bankroll=bankroll)
        
        # Parse sports filter
        sports_list = None
        if sports:
            sports_list = [s.strip().upper() for s in sports.split(",") if s.strip()]
        
        # Parse models (if you want to pass to engine in future)
        # For now, engine uses all models by default
        
        recommendations = await engine.get_todays_recommendations(
            min_confidence=min_confidence,
            sports=sports_list
        )
        
        logger.info(f"Generated {len(recommendations.get('singles', []))} recommendations")
        
    except Exception as e:
        logger.error(f"Recommendations generation failed: {e}", exc_info=True)
        recommendations = {
            "singles": [],
            "parlays": [],
            "summary": {
                "error": str(e)[:200],
                "games_analyzed": 0,
                "recommendations": 0
            }
        }

    # Combine everything
    return {
        **recommendations,
        "fresh_data": scrape_summary,
        "stats_scrape": stats_summary,
        "data_freshness": "LIVE" if scrape_summary.get("success") else "CACHED",
        "bankroll_used": bankroll,
        "models_requested": models,
        "min_confidence_used": min_confidence
    }


@router.get("/recommendations")
@redis_cache(ttl=60)
async def get_recommendations(
    models: str = Query(default="all", description="Model selection (legacy param, uses all models)"),
    min_confidence: float = Query(default=60, ge=0, le=100, description="Minimum confidence threshold"),
    sports: Optional[str] = Query(default=None, description="Comma-separated sports filter"),
    bankroll: float = Query(default=DEFAULT_BANKROLL, gt=0, description="Bankroll for Kelly sizing"),
    session: AsyncSession = Depends(get_db),
):
    """
    **Get AI betting recommendations (uses existing cached data).**
    
    This is faster than refresh-and-calculate as it doesn't scrape fresh data.
    Use this for quick checks or when data was recently refreshed.
    
    Query Parameters:
    - models: (legacy, kept for compatibility)
    - min_confidence: Min confidence % (default: 60)
    - sports: Filter by sports (e.g., "NBA,NFL")
    - bankroll: Your bankroll for bet sizing (default: $1000)
    
    Returns:
    - singles: Single bet recommendations
    - parlays: Parlay recommendations
    - summary: Statistics and metadata
    """
    logger.info(f"Getting recommendations (min_confidence={min_confidence}, sports={sports})")
    
    try:
        engine = RecommendationsEngine(session, bankroll=bankroll)
        
        # Parse sports filter
        sports_list = None
        if sports:
            sports_list = [s.strip().upper() for s in sports.split(",") if s.strip()]
        
        recommendations = await engine.get_todays_recommendations(
            min_confidence=min_confidence,
            sports=sports_list
        )
        
        # Add metadata
        recommendations['bankroll_used'] = bankroll
        recommendations['min_confidence_used'] = min_confidence
        recommendations['sports_filter'] = sports_list
        recommendations['data_source'] = "cached"
        
        logger.info(f"Returned {len(recommendations.get('singles', []))} recommendations")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Recommendations generation failed: {e}", exc_info=True)
        return {
            "singles": [],
            "parlays": [],
            "summary": {
                "error": str(e)[:200],
                "games_analyzed": 0,
                "recommendations": 0
            }
        }


@router.get("/verify-before-bet/{game_id}")
async def verify_before_bet(
    game_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    **Pre-bet verification for a specific game.**
    
    Fetches fresh data for the specified game:
    - Latest injuries
    - Weather forecast
    - Current odds
    - Game status (not postponed/cancelled)
    
    Use this before placing a real bet to ensure nothing has changed.
    
    Path Parameters:
    - game_id: Game ID to verify
    
    Returns:
    - verified: Boolean if game is safe to bet
    - game: Game details
    - verification: Fresh data checks
    - recommendations: Warnings or go-ahead signal
    """
    logger.info(f"Verifying game {game_id} before bet placement")
    
    verifier = PreBetVerifier(session)
    try:
        result = await verifier.verify_game(game_id)
        
        # Add recommendation based on verification
        if result.get('verified'):
            rec = result.get('recommendations', {})
            confidence_level = rec.get('confidence_level', 'unknown')
            
            logger.info(f"Game {game_id} verification: {confidence_level}")
        else:
            logger.warning(f"Game {game_id} failed verification: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Verification failed for game {game_id}: {e}", exc_info=True)
        return {
            "verified": False,
            "error": str(e)[:200],
            "game_id": game_id
        }
    finally:
        await verifier.close()


@router.get("/models")
async def get_available_models():
    """
    **Get information about available betting models.**
    
    Returns details about each statistical model used in recommendations.
    
    Returns:
    - models: List of available models with descriptions
    - weights: Model weights in consensus calculation
    - recommendation: How to use the models parameter
    """
    return {
        "models": [
            {
                "id": "elo",
                "name": "Elo Rating Model",
                "description": "Team strength based on win/loss record with home advantage",
                "weight": 0.30,
                "use_case": "General team strength assessment"
            },
            {
                "id": "pythagorean",
                "name": "Pythagorean Expectation",
                "description": "Win probability from points scored/allowed ratio",
                "weight": 0.25,
                "use_case": "Offensive/defensive matchup analysis"
            },
            {
                "id": "recent_form",
                "name": "Recent Form Model",
                "description": "Weighted win rate from last 10 games",
                "weight": 0.20,
                "use_case": "Hot/cold streak detection"
            },
            {
                "id": "home_advantage",
                "name": "Home Advantage Model",
                "description": "Sport-specific home court/field advantage",
                "weight": 0.10,
                "use_case": "Home/away impact"
            },
            {
                "id": "vegas",
                "name": "Vegas Consensus",
                "description": "Devigged market odds (sharp money indicator)",
                "weight": 0.15,
                "use_case": "Market baseline and value detection"
            }
        ],
        "total_weight": 1.00,
        "consensus_method": "Weighted average of all available models",
        "confidence_calculation": "Model agreement + edge magnitude",
        "recommendation": "All models are used by default for best accuracy"
    }


@router.get("/health")
async def health_check():
    """
    **Health check endpoint.**
    
    Quick check to verify the AAI Bets service is running.
    """
    return {
        "status": "healthy",
        "service": "aai-bets",
        "version": "2.0.0",
        "features": [
            "fresh_data_scraping",
            "multi_model_recommendations",
            "kelly_criterion_sizing",
            "value_detection",
            "pre_bet_verification"
        ]
    }