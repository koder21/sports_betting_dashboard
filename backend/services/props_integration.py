"""
Integration of web-scraped props into the fresh data pipeline.

This service runs daily alongside FreshDataScraper to get player props
from FanDuel, BetMGM, TheScore, and ESPN (with fallbacks).
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .props_web_scraper import PropScraper, scrape_daily_props

logger = logging.getLogger(__name__)


class PropsIntegrationService:
    """
    Integrate web-scraped props into your betting dashboard.
    
    Usage:
        props_service = PropsIntegrationService(db_session)
        result = await props_service.update_props_for_sports(["NBA", "NFL"])
        # result: {
        #     "NBA": {"props_count": 45, "source": "fanduel", "success": true},
        #     "NFL": {"props_count": 23, "source": "betmgm", "success": true},
        # }
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def update_props_for_sports(self, sports: List[str]) -> Dict[str, Any]:
        """
        Update props for given sports.
        
        Args:
            sports: ["NBA", "NFL", "NHL", etc.]
        
        Returns:
            Summary of scrape results
        """
        logger.info(f"Updating props for: {sports}")
        
        # Scrape from all sources with fallbacks
        scrape_results = await scrape_daily_props(sports)
        
        summary = {}
        
        for sport, result in scrape_results.items():
            try:
                if result['success'] and result['props']:
                    # Store props in database/cache
                    await self._store_props(sport, result['props'])
                    
                    summary[sport] = {
                        "props_count": len(result['props']),
                        "source": result['source'],
                        "success": True,
                        "errors": result.get('errors', [])
                    }
                    
                    logger.info(
                        f"{sport}: {len(result['props'])} props from {result['source']}"
                    )
                else:
                    summary[sport] = {
                        "props_count": 0,
                        "source": "none",
                        "success": False,
                        "errors": result.get('errors', ['No props found'])
                    }
                    logger.warning(f"{sport} scrape failed: {result.get('errors')}")
            
            except Exception as e:
                logger.error(f"Error processing {sport} props: {e}")
                summary[sport] = {
                    "props_count": 0,
                    "source": "error",
                    "success": False,
                    "errors": [str(e)]
                }
        
        return summary
    
    async def _store_props(self, sport: str, props: List[Dict[str, Any]]):
        """
        Store props in database/cache.
        
        For now, this is a placeholder. You can:
        1. Store in database table
        2. Store in Redis cache
        3. Store in memory for session
        
        Later: integrate with your database when ready.
        """
        logger.info(f"Storing {len(props)} {sport} props")
        
        # Example: Store in database
        # for prop in props:
        #     db_prop = Prop(
        #         player_name=prop['player_name'],
        #         prop_type=prop['prop_type'],
        #         over_odds=prop['over_odds'],
        #         under_odds=prop['under_odds'],
        #         sportsbook=prop['sportsbook'],
        #         sport=sport,
        #         updated_at=datetime.now(timezone.utc)
        #     )
        #     self.session.add(db_prop)
        # await self.session.commit()
    
    async def get_player_props(self, player_name: str, sport: str) -> List[Dict[str, Any]]:
        """
        Get props for a specific player.
        
        Example:
            props = await service.get_player_props("LeBron James", "NBA")
            # Returns: [
            #     {
            #         "player_name": "LeBron James",
            #         "prop_type": "Points",
            #         "over_odds": 1.90,
            #         "under_odds": 1.90,
            #         "sportsbook": "FanDuel"
            #     },
            #     ...
            # ]
        """
        # Fetch from database/cache
        # This is a placeholder - implement based on your storage choice
        return []
    
    async def get_game_props(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Get all props for a specific game.
        """
        # Fetch props for players in this game
        return []


async def scrape_props_task():
    """
    Daily task to scrape props from all sources.
    
    Add to your scheduler (tasks.py):
    
        # In your scheduler setup
        scheduler.add_job(
            scrape_props_task,
            'cron',
            hour=8,  # 8 AM daily
            minute=0,
            args=[],
            name='Scrape Player Props'
        )
    """
    try:
        logger.info("Starting daily props scrape")
        
        sports = ["NBA", "NFL", "NHL", "MLB", "NCAAB", "NCAAF"]
        result = await scrape_daily_props(sports)
        
        # Log summary
        for sport, data in result.items():
            if data['success']:
                logger.info(
                    f"✅ {sport}: {len(data['props'])} props from {data['source']}"
                )
            else:
                logger.warning(
                    f"❌ {sport}: Failed - {data.get('errors')}"
                )
        
        return result
    
    except Exception as e:
        logger.error(f"Props scrape task failed: {e}")
        return {}
