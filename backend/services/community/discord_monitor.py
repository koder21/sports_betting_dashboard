"""
Discord betting channel monitor
Receives webhooks from Discord or scrapes public Discord messages
"""
from datetime import datetime
from typing import Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

class DiscordPropMonitor:
    """Monitors Discord channels for prop betting discussions"""
    
    def __init__(self):
        self.channels_config = {
            # "channel_name": "webhook_url"
            # Users can configure Discord webhooks to send data here
        }
    
    async def process_discord_message(
        self,
        message_content: str,
        channel_name: str,
        author: str
    ) -> List[Dict]:
        """
        Process a Discord message and extract props
        Discord messages are typically more casual/conversational
        """
        props = []
        
        # Simple pattern: "Player Name over/under line"
        # e.g., "LeBron over 25.5" or "Kelce U 60.5 yards"
        pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(over|under|o|u)\s*(\d+\.?\d*)\s*(?:([a-z\s]+))?"
        
        for match in re.finditer(pattern, message_content, re.IGNORECASE):
            player_name = match.group(1).strip()
            direction = match.group(2).lower()
            line = float(match.group(3))
            stat_type = match.group(4).strip() if match.group(4) else "points"
            
            stat_type = self._normalize_stat_type(stat_type)
            if not stat_type:
                continue
            
            props.append({
                "player_name": player_name,
                "market": stat_type,
                "line": line,
                "direction": "over" if direction in ["o", "over"] else "under",
                "source": "discord",
                "channel": channel_name,
                "author": author,
                "mentioned_at": datetime.utcnow().isoformat(),
            })
        
        return props
    
    def _normalize_stat_type(self, stat: str) -> Optional[str]:
        """Normalize stat type name"""
        stat = stat.lower().strip()
        
        if any(s in stat for s in ["point", "pts", "pt"]):
            return "points"
        elif any(s in stat for s in ["rebound", "reb"]):
            return "rebounds"
        elif any(s in stat for s in ["assist", "ast"]):
            return "assists"
        elif any(s in stat for s in ["pass"]):
            return "passing_yards"
        elif any(s in stat for s in ["rush"]):
            return "rushing_yards"
        elif any(s in stat for s in ["rec", "receiving"]):
            return "receiving_yards"
        elif any(s in stat for s in ["yard", "yds"]):
            return "total_yards"
        
        return None
    
    async def add_webhook(self, channel_name: str, webhook_url: str):
        """Register a Discord webhook"""
        self.channels_config[channel_name] = webhook_url
        logger.info(f"Added Discord webhook for {channel_name}")
    
    async def get_configured_channels(self) -> List[str]:
        """Get list of monitored Discord channels"""
        return list(self.channels_config.keys())
