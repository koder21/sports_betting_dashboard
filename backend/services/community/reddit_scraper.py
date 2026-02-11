"""
Reddit prop mention scraper
Scrapes r/sportsbooks, r/nba, r/nfl for popular prop discussions
"""
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import xml.etree.ElementTree as ET
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class RedditPropScraper:
    """Scrapes Reddit for prop betting discussions"""
    
    # Subreddits to monitor
    SUBREDDITS = ["sportsbooks", "nba", "nfl", "mlb", "nhl", "sportsbetting"]
    
    # Regex patterns for prop extraction
    PROP_PATTERNS = {
        "points": r"(\d+\.?\d*)\s*(?:pts?|points)",
        "rebounds": r"(\d+\.?\d*)\s*(?:reb|rebounds)",
        "assists": r"(\d+\.?\d*)\s*(?:ast|assists)",
        "passing_yards": r"(\d+\.?\d*)\s*(?:pass yds?|passing yards)",
        "rushing_yards": r"(\d+\.?\d*)\s*(?:rush yds?|rushing yards)",
        "receiving_yards": r"(\d+\.?\d*)\s*(?:rec yds?|receiving yards)",
        "strikeouts": r"(\d+\.?\d*)\s*(?:so|strikeouts|k's?)",
        "hits": r"(\d+\.?\d*)\s*(?:hits?)",
    }
    
    # Keywords that indicate over/under
    OU_KEYWORDS = [
        r"over\s*(\d+\.?\d*)",
        r"under\s*(\d+\.?\d*)",
        r"o\s*(\d+\.?\d*)",
        r"u\s*(\d+\.?\d*)",
        r">[\s=]*(\d+\.?\d*)",
        r"<[\s=]*(\d+\.?\d*)",
    ]
    
    # Player name patterns (common formats)
    PLAYER_PATTERNS = [
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",  # Firstname Lastname or just Firstname
    ]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.pushshift.io/reddit/search/submission"
        self.reddit_search_urls = [
            "https://www.reddit.com/r/{subreddit}/search.json",
            "https://old.reddit.com/r/{subreddit}/search.json",
        ]
        self.reddit_new_urls = [
            "https://www.reddit.com/r/{subreddit}/new.json",
            "https://old.reddit.com/r/{subreddit}/new.json",
        ]
        self.reddit_hot_urls = [
            "https://www.reddit.com/r/{subreddit}.json",
            "https://old.reddit.com/r/{subreddit}.json",
        ]
        self.reddit_rss_urls = [
            "https://www.reddit.com/r/{subreddit}/new/.rss",
            "https://old.reddit.com/r/{subreddit}/new/.rss",
        ]
        self.user_agent = "sports-betting-dashboard/1.0"
        self.pushshift_disabled = False
        self.reddit_disabled = False
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def scrape_subreddit(
        self, 
        subreddit: str, 
        time_filter: str = "day",
        limit: int = 100
    ) -> List[Dict]:
        """
        Scrape a subreddit for prop discussions
        time_filter: 'day', 'week', 'month'
        """
        if not self.session:
            await self.initialize()
        
        try:
            if self.reddit_disabled:
                return []
            if self.pushshift_disabled:
                return await self._scrape_reddit_search(subreddit, time_filter, limit)
            # Use Pushshift API (free, no auth required)
            params = {
                "subreddit": subreddit,
                "sort": "comments",  # Most commented posts
                "sort_type": "desc",
                "size": limit,
                "type": "submission"
            }
            
            # Set time window
            now = datetime.utcnow()
            if time_filter == "day":
                since = (now - timedelta(days=1)).timestamp()
            elif time_filter == "week":
                since = (now - timedelta(days=7)).timestamp()
            else:  # month
                since = (now - timedelta(days=30)).timestamp()
            
            params["after"] = int(since)
            
            async with self.session.get(self.base_url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"Pushshift API returned {resp.status}")
                    if resp.status in (403, 404, 429, 522):
                        self.pushshift_disabled = True
                    return await self._scrape_reddit_search(subreddit, time_filter, limit)
                
                data = await resp.json()
                posts = data.get("data", [])
                
                return self._extract_props_from_posts(posts, subreddit)
        
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {e}")
            self.pushshift_disabled = True
            return await self._scrape_reddit_search(subreddit, time_filter, limit)

    async def _scrape_reddit_search(
        self,
        subreddit: str,
        time_filter: str,
        limit: int
    ) -> List[Dict]:
        """Fallback to Reddit public JSON search when Pushshift fails."""
        if not self.session:
            await self.initialize()

        query = "(over OR under OR props OR prop OR pick OR bet)"
        params = {
            "q": query,
            "restrict_sr": 1,
            "sort": "new",
            "t": time_filter,
            "limit": min(limit, 100),
            "raw_json": 1,
        }

        try:
            for url_tpl in self.reddit_search_urls:
                url = url_tpl.format(subreddit=subreddit)
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Reddit search returned {resp.status}")
                        continue
                    data = await resp.json()
                    children = (data.get("data") or {}).get("children") or []
                    posts = [c.get("data", {}) for c in children]
                    return self._extract_props_from_posts(posts, subreddit)
            return await self._scrape_reddit_new(subreddit, limit)
        except Exception as e:
            logger.error(f"Reddit search error for r/{subreddit}: {e}")
            return await self._scrape_reddit_new(subreddit, limit)

    async def _scrape_reddit_new(self, subreddit: str, limit: int) -> List[Dict]:
        """Fallback to subreddit /new listing."""
        if not self.session:
            await self.initialize()

        params = {
            "limit": min(limit, 100),
            "raw_json": 1,
        }

        try:
            for url_tpl in self.reddit_new_urls:
                url = url_tpl.format(subreddit=subreddit)
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Reddit new returned {resp.status}")
                        continue
                    data = await resp.json()
                    children = (data.get("data") or {}).get("children") or []
                    posts = [c.get("data", {}) for c in children]
                    return self._extract_props_from_posts(posts, subreddit)
            return await self._scrape_reddit_hot(subreddit, limit)
        except Exception as e:
            logger.error(f"Reddit new error for r/{subreddit}: {e}")
            return await self._scrape_reddit_hot(subreddit, limit)

    async def _scrape_reddit_hot(self, subreddit: str, limit: int) -> List[Dict]:
        """Fallback to subreddit hot listing."""
        if not self.session:
            await self.initialize()

        params = {
            "limit": min(limit, 100),
            "raw_json": 1,
        }

        try:
            for url_tpl in self.reddit_hot_urls:
                url = url_tpl.format(subreddit=subreddit)
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Reddit hot returned {resp.status}")
                        continue
                    data = await resp.json()
                    children = (data.get("data") or {}).get("children") or []
                    posts = [c.get("data", {}) for c in children]
                    return self._extract_props_from_posts(posts, subreddit)
            return await self._scrape_reddit_rss(subreddit, limit)
        except Exception as e:
            logger.error(f"Reddit hot error for r/{subreddit}: {e}")
            return await self._scrape_reddit_rss(subreddit, limit)

    async def _scrape_reddit_rss(self, subreddit: str, limit: int) -> List[Dict]:
        """Fallback to subreddit RSS feed."""
        if not self.session:
            await self.initialize()

        try:
            for url_tpl in self.reddit_rss_urls:
                url = url_tpl.format(subreddit=subreddit)
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"Reddit RSS returned {resp.status}")
                        continue
                    xml_text = await resp.text()
                    posts = self._parse_rss_posts(xml_text)
                    return self._extract_props_from_posts(posts[:limit], subreddit)
        except Exception as e:
            logger.error(f"Reddit RSS error for r/{subreddit}: {e}")
        # If all reddit endpoints fail, disable reddit scraping to prevent log spam
        self.reddit_disabled = True
        logger.warning("Reddit endpoints unavailable; disabling reddit scraping")
        return []

    def _parse_rss_posts(self, xml_text: str) -> List[Dict]:
        """Parse RSS/Atom into post-like dicts."""
        posts: List[Dict] = []
        try:
            root = ET.fromstring(xml_text)

            # Atom feed
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                summary_el = entry.find("{http://www.w3.org/2005/Atom}content")
                title = title_el.text if title_el is not None else ""
                summary = summary_el.text if summary_el is not None else ""
                posts.append({"title": title or "", "selftext": summary or ""})

            # RSS feed
            for item in root.findall(".//item"):
                title_el = item.find("title")
                desc_el = item.find("description")
                title = title_el.text if title_el is not None else ""
                summary = desc_el.text if desc_el is not None else ""
                posts.append({"title": title or "", "selftext": summary or ""})
        except Exception:
            return []

        return posts

    def _extract_props_from_posts(self, posts: List[Dict], subreddit: str) -> List[Dict]:
        """Extract props from a list of post dictionaries."""
        all_props = []
        for post in posts:
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            full_text = f"{title} {selftext}".lower()

            # Only process if contains betting keywords
            if any(kw in full_text for kw in ["over", "under", "props", "prop", "pick", "bet"]):
                props = self._extract_props_from_text(full_text, subreddit)
                all_props.extend(props)

        return all_props
    
    def _extract_props_from_text(self, text: str, subreddit: str) -> List[Dict]:
        """Extract individual props from Reddit text"""
        props = []
        
        # Look for player name + stat combination
        # Simple pattern: "Player Name over 20.5 points"
        pattern = r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(over|under|o|u)\s*(\d+\.?\d*)\s*(\w+)"
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            player_name = match.group(1).strip()
            direction = match.group(2).lower()
            line = float(match.group(3))
            stat_type = match.group(4).lower()
            
            # Normalize stat type
            stat_type = self._normalize_stat_type(stat_type)
            if not stat_type:
                continue
            
            props.append({
                "player_name": player_name,
                "market": stat_type,
                "line": line,
                "direction": "over" if direction in ["o", "over"] else "under",
                "source": "reddit",
                "subreddit": subreddit,
                "mentioned_at": datetime.utcnow().isoformat(),
            })
        
        return props
    
    def _normalize_stat_type(self, stat: str) -> Optional[str]:
        """Normalize stat type name"""
        stat = stat.lower().strip()
        
        # Map variations to canonical names
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
        elif any(s in stat for s in ["strike", "k's", "so"]):
            return "strikeouts"
        elif any(s in stat for s in ["hit"]):
            return "hits"
        
        return None
    
    async def get_trending_props(
        self,
        time_filter: str = "day",
        min_mentions: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Get trending props across all subreddits
        Returns: {prop_key: [mention data...]}
        """
        all_props = []
        
        for subreddit in self.SUBREDDITS:
            props = await self.scrape_subreddit(subreddit, time_filter)
            all_props.extend(props)
        
        # Group by prop (player + market + line)
        grouped = {}
        for prop in all_props:
            key = f"{prop['player_name']}_{prop['market']}_{prop['line']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(prop)
        
        # Filter by minimum mentions
        trending = {
            k: v for k, v in grouped.items() 
            if len(v) >= min_mentions
        }
        
        return trending
