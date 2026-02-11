"""
Community Insights API endpoints - DISABLED
Feature under construction
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/trending")
async def get_trending_props():
    """Feature under construction"""
    return {
        "trending": [],
        "metadata": {
            "status": "under_construction",
            "message": "Community Insights feature coming soon"
        }
    }


@router.get("/trending/{sport}")
async def get_trending_by_sport(sport: str):
    """Feature under construction"""
    return {
        "trending": [],
        "metadata": {
            "status": "under_construction",
            "message": f"Community Insights for {sport} coming soon"
        }
    }


@router.get("/stats")
async def get_insight_stats():
    """Feature under construction"""
    return {
        "status": "under_construction",
        "message": "Stats coming soon"
    }


@router.post("/discord/webhook")
async def process_discord_webhook():
    """Feature under construction"""
    return {
        "status": "under_construction",
        "message": "Discord integration coming soon"
    }
