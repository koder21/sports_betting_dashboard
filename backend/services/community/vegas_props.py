"""
Vegas prop aggregator
Pulls featured/popular props from sportsbook odds
Uses data already available from props scrapers
"""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import logging

logger = logging.getLogger(__name__)

class VegasPropAggregator:
    """Aggregates Vegas featured props"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_featured_props(self) -> List[Dict]:
        """
        Get currently featured props from sportsbooks
        These are typically props with:
        - High action/movement
        - Popular betting interest
        - Balanced books (lots of action both sides)
        """
        # This would integrate with your existing props scraper data
        # For now, returns high-action props based on recent scrapes
        
        props = []
        # TODO: Integrate with existing props_dk_enhanced.py or props_web_scraper.py
        # to pull featured props that sportsbooks are promoting
        
        return props
    
    async def get_line_movement(
        self,
        player_name: str,
        market: str
    ) -> Optional[Dict]:
        """
        Get line movement history for a prop
        Shows if sharp money is backing a side
        """
        # TODO: Store line movement history in database
        # Track line movements over time to detect sharp action
        return None
    
    async def get_popular_props_by_sport(
        self,
        sport: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get most popular props for a sport
        Popularity = frequency in odds updates, action volume
        """
        props = []
        # TODO: Query props by frequency of appearance in latest odds updates
        
        return props
