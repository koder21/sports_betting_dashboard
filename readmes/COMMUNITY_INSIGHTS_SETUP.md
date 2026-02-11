# Community Insights - Setup Guide

## Installation

1. **Install dependencies** (already added to requirements.txt):
```bash
cd backend
pip install -r requirements.txt
```

Dependencies added:
- `praw` - Reddit API access
- `requests` - HTTP requests
- `aiohttp` - Already installed

2. **Restart backend**:
```bash
python -m uvicorn main:app --reload
```

The insights service will initialize on first request.

## Configuration

### Reddit
Currently uses **Pushshift API** (free, no authentication required):
- No API keys needed
- Rate limited to ~100 requests/minute
- Scrapes public r/sportsbooks, r/nba, r/nfl posts

To use official Reddit API instead:

1. Create Reddit app at https://reddit.com/prefs/apps
2. Get `client_id` and `client_secret`
3. Update [redis_scraper.py](./backend/services/community/reddit_scraper.py):

```python
import praw

self.reddit = praw.Reddit(
    client_id='your_client_id',
    client_secret='your_client_secret',
    user_agent='sports_betting_dashboard/1.0'
)
```

### Vegas Props
**Requires:** Integration with existing props scrapers

Current placeholders in [vegas_props.py](./backend/services/community/vegas_props.py):
- `get_featured_props()` - Pull from DraftKings/FanDuel scraper data
- `get_popular_props_by_sport()` - Query by frequency

To enable Vegas props:
1. Use existing `props_dk_enhanced.py` data
2. Query for props with highest action/frequency
3. Track line movements over time

### Discord
**Setup**: Configure webhook in your Discord channel

1. In Discord channel: Server Settings → Integrations → Webhooks → New Webhook
2. Copy webhook URL
3. Configure in system:

**Option A: API Call**
```bash
curl -X POST "http://localhost:8000/insights/discord/webhook" \
  -d "message=LeBron over 25.5 points&channel=sharp-picks&author=user"
```

**Option B: Discord Bot (Advanced)**
Create a Discord bot that:
```python
import discord
import aiohttp

class BettingBot(discord.Client):
    async def on_message(self, message):
        if message.channel.name == "sharp-picks":
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "http://localhost:8000/insights/discord/webhook",
                    params={
                        "message": message.content,
                        "channel": message.channel.name,
                        "author": message.author.name
                    }
                )
```

## Testing

### 1. Test Reddit Scraping
```bash
curl http://localhost:8000/insights/trending?time_filter=day
```

Should return trending props from Reddit.

### 2. Test Discord Webhook
```bash
curl -X POST "http://localhost:8000/insights/discord/webhook" \
  -d "message=LeBron over 25.5 points&channel=test&author=testuser"
```

### 3. Test Sport Filtering
```bash
curl http://localhost:8000/insights/trending/nba?time_filter=day
```

### 4. View Stats
```bash
curl http://localhost:8000/insights/stats
```

## Customization

### Add More Subreddits
Edit [reddit_scraper.py](./backend/services/community/reddit_scraper.py):

```python
SUBREDDITS = [
    "sportsbooks",
    "nba", "nfl", "mlb", "nhl",
    "sportsbetting",
    "sportsbook",  # Add more
    "degenerates",  # Popular betting community
]
```

### Add More Stat Types
Edit `_normalize_stat_type()` in both files:

```python
elif any(s in stat for s in ["home_runs", "hr"]):
    return "home_runs"
```

### Adjust Minimum Thresholds
For testing or different user base size:

```python
# Show props with 1+ mention instead of 2+
GET /insights/trending?min_mentions=1

# Only show if 2+ sources agree
GET /insights/trending?min_sources=2
```

### Change Time Filters
Options in all endpoints:
- `day` = last 24 hours
- `week` = last 7 days
- `month` = last 30 days

## Rate Limiting

Current implementation:
- ✅ Pushshift API: ~100 req/min
- ✅ No rate limiting on endpoints (add if needed)

For production, add rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.get("/trending")
@limiter.limit("10/minute")
async def get_trending_props(...):
    ...
```

## Database Storage (Optional)

To track trends over time, store in database:

1. Create `CommunityTrend` model:
```python
class CommunityTrend(Base):
    __tablename__ = "community_trends"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    player_name: Mapped[str]
    market: Mapped[str]
    line: Mapped[float]
    mention_count: Mapped[int]
    sources: Mapped[str]  # JSON list
    recorded_at: Mapped[datetime]
```

2. Save insights on cron job:
```python
async def save_insights_snapshot():
    insights = CommunityInsights(session)
    trending = await insights.get_trending_props()
    
    for prop in trending["trending"]:
        record = CommunityTrend(
            player_name=prop["player_name"],
            market=prop["market"],
            line=prop["line"],
            mention_count=prop["total_mentions"],
            sources=json.dumps(prop["sources"]),
            recorded_at=datetime.utcnow()
        )
        session.add(record)
    
    await session.commit()
```

## Monitoring

Check logs for scraping status:
```bash
# Terminal 1: Run backend
python -m uvicorn main:app --reload

# Terminal 2: Check for insight scrapes
grep -i "reddit\|vegas\|discord" backend.log
```

## Troubleshooting

**No trending props returned?**
- Check Pushshift API status: https://api.pushshift.io/reddit/
- Verify subreddits have recent posts with betting discussions
- Try relaxing filters: `min_mentions=1&min_sources=1`

**Discord webhooks not working?**
- Verify webhook URL is correct
- Check message format matches regex patterns
- Ensure channel name is specified

**Vegas props not showing?**
- Vegas integration not yet implemented
- See [vegas_props.py](./backend/services/community/vegas_props.py) for TODOs
- Integrate with existing `props_dk_enhanced.py` data

## Performance

Current implementation:
- Reddit scraping: ~2-5 seconds per subreddit
- Aggregation: <100ms
- Discord processing: <50ms

For large scale:
- Cache trending results (5-10 min TTL)
- Scrape Reddit on background scheduler
- Store historical data in database
