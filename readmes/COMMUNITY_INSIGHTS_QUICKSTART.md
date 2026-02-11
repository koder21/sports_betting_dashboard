# Community Insights - Quick Start

## 3 Simple Steps

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Restart Backend
```bash
python -m uvicorn main:app --reload
```

### 3. Try It Out

**Get trending props:**
```bash
curl http://localhost:8000/insights/trending?time_filter=day
```

**Get NBA trending:**
```bash
curl http://localhost:8000/insights/trending/nba?time_filter=day
```

**Get stats:**
```bash
curl http://localhost:8000/insights/stats
```

## In Your Frontend

Add the component:
```jsx
import CommunityInsights from './components/CommunityInsights';

// In your page
<CommunityInsights />
```

## What It Shows

Shows trending player props from:
- 🔴 **Reddit** - r/sportsbooks, r/nba, r/nfl discussions
- 📊 **Vegas** - Featured sportsbook props (future: integration pending)
- 💬 **Discord** - Webhook integration for Discord channels

## Customize

### Adjust Filters
```bash
# Only show props from 2+ sources
curl http://localhost:8000/insights/trending?min_sources=2

# Only show props with 5+ mentions
curl http://localhost:8000/insights/trending?min_mentions=5

# Last 7 days instead of 24h
curl http://localhost:8000/insights/trending?time_filter=week
```

### Add More Subreddits
Edit `backend/services/community/reddit_scraper.py`:
```python
SUBREDDITS = ["sportsbooks", "nba", "nfl", "mlb", "nhl", "your_subreddit"]
```

### Add Discord Webhook
```bash
curl -X POST "http://localhost:8000/insights/discord/webhook" \
  -d "message=LeBron over 25.5&channel=sharp-picks&author=user"
```

## Full Documentation

- **[COMMUNITY_INSIGHTS_README.md](./COMMUNITY_INSIGHTS_README.md)** - Features & API docs
- **[COMMUNITY_INSIGHTS_SETUP.md](./COMMUNITY_INSIGHTS_SETUP.md)** - Detailed setup & config
