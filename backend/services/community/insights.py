"""
Community Insights aggregator
Combines Reddit, Vegas, and Discord data into trending props
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
import logging

# from .reddit_scraper import RedditPropScraper  # Disabled - 403/404 errors
from .vegas_props import VegasPropAggregator
from .discord_monitor import DiscordPropMonitor

logger = logging.getLogger(__name__)

class CommunityInsights:
    """Aggregates community betting insights from multiple sources"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        # self.reddit = RedditPropScraper()  # Disabled - 403/404 errors
        self.vegas = VegasPropAggregator(session)
        self.discord = DiscordPropMonitor()
    
    async def initialize(self):
        """Initialize scrapers"""
        pass  # Reddit disabled
    
    async def close(self):
        """Cleanup"""
        pass  # Reddit disabled
    
    async def get_trending_props(
        self,
        time_filter: str = "day",
        min_sources: int = 1,
        min_mentions: int = 2
    ) -> Dict:
        """
        Get trending props across all sources
        
        time_filter: 'day', 'week', 'month'
        min_sources: Minimum number of different sources that mention a prop
        min_mentions: Minimum number of times a prop must be mentioned
        """
        
        all_props = []
        
        # Get Reddit props - DISABLED (403/404 errors)
        # try:
        #     reddit_trending = await self.reddit.get_trending_props(
        #         time_filter=time_filter,
        #         min_mentions=1
        #     )
        #     for key, mentions in reddit_trending.items():
        #         for mention in mentions:
        #             mention["source"] = "reddit"
        #             all_props.append(mention)
        #     logger.info(f"Found {len(reddit_trending)} trending props on Reddit")
        # except Exception as e:
        #     logger.error(f"Error scraping Reddit: {e}")
        logger.info("Reddit scraping disabled")
        
        # Get Vegas featured props
        try:
            vegas_props = await self.vegas.get_featured_props()
            all_props.extend(vegas_props)
            logger.info(f"Found {len(vegas_props)} featured Vegas props")
        except Exception as e:
            logger.error(f"Error getting Vegas props: {e}")
        
        # Format and aggregate
        result = self._aggregate_props(
            all_props,
            min_sources=min_sources,
            min_mentions=min_mentions
        )
        
        result["metadata"] = {
            "time_filter": time_filter,
            "updated_at": datetime.utcnow().isoformat(),
            "min_sources": min_sources,
            "min_mentions": min_mentions,
            "sources": ["vegas", "discord"],  # reddit disabled
        }
        
        return result
    
    def _aggregate_props(
        self,
        props: List[Dict],
        min_sources: int = 1,
        min_mentions: int = 2
    ) -> Dict:
        """Aggregate props by player/market/line"""
        
        # Group by prop key
        grouped = defaultdict(list)
        
        for prop in props:
            # Normalize player name for matching
            player_normalized = prop["player_name"].lower().strip()
            market = prop["market"].lower()
            line = prop["line"]
            
            key = f"{player_normalized}|{market}|{line}"
            grouped[key].append(prop)
        
        # Calculate stats for each prop
        trending = []
        
        for key, mentions in grouped.items():
            parts = key.split("|")
            player_name = parts[0].title()
            market = parts[1]
            line = float(parts[2])
            
            # Count sources
            sources = set(m.get("source", "unknown") for m in mentions)
            
            # Skip if doesn't meet minimum thresholds
            if len(sources) < min_sources or len(mentions) < min_mentions:
                continue
            
            # Count directions
            over_count = sum(1 for m in mentions if m.get("direction") == "over")
            under_count = sum(1 for m in mentions if m.get("direction") == "under")
            
            # Build result
            trending.append({
                "player_name": player_name,
                "market": market,
                "line": line,
                "total_mentions": len(mentions),
                "sources": list(sources),
                "source_count": len(sources),
                "over_consensus": over_count,
                "under_consensus": under_count,
                "consensus_direction": "over" if over_count > under_count else "under" if under_count > over_count else "mixed",
                "mentions": mentions,
            })
        
        # Sort by mentions + source count
        trending.sort(
            key=lambda x: (x["source_count"], x["total_mentions"]),
            reverse=True
        )
        
        return {
            "trending": trending,
            "total_unique_props": len(trending),
        }
    
    async def get_trending_by_sport(
        self,
        sport: str,
        time_filter: str = "day"
    ) -> Dict:
        """Get trending props for a specific sport"""
        
        all_props = []
        
        # Get Reddit props for relevant subreddits - DISABLED (403/404 errors)
        # sport_subreddits = {
        #     "nba": ["nba", "sportsbooks"],
        #     "nfl": ["nfl", "sportsbooks"],
        #     "mlb": ["mlb", "sportsbooks"],
        #     "nhl": ["nhl", "sportsbooks"],
        # }
        # 
        # if sport.lower() in sport_subreddits:
        #     for subreddit in sport_subreddits[sport.lower()]:
        #         try:
        #             props = await self.reddit.scrape_subreddit(
        #                 subreddit,
        #                 time_filter=time_filter,
        #                 limit=50
        #             )
        #             all_props.extend(props)
        #         except Exception as e:
        #             logger.error(f"Error scraping r/{subreddit}: {e}")
        
        logger.info(f"Reddit scraping disabled for {sport}")
        
        # Get Vegas props for sport
        try:
            vegas_props = await self.vegas.get_popular_props_by_sport(sport)
            all_props.extend(vegas_props)
        except Exception as e:
            logger.error(f"Error getting Vegas props for {sport}: {e}")
        
        return self._aggregate_props(all_props, min_sources=1, min_mentions=1)
    
    async def process_discord_webhook(
        self,
        message_content: str,
        channel_name: str,
        author: str
    ) -> List[Dict]:
        """Process incoming Discord message"""
        
        props = await self.discord.process_discord_message(
            message_content,
            channel_name,
            author
        )
        
        logger.info(f"Processed Discord message from {channel_name}: {len(props)} props extracted")
        return props
