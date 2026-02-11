# Community Insights - User Guide

**Community Insights** shows what's trending in the betting community across three major sources:

- 🔴 **Reddit** - r/sportsbooks, r/nba, r/nfl, r/mlb discussions
- 📊 **Vegas** - Featured props from sportsbooks
- 💬 **Discord** - Sharp bettors' picks from betting Discord channels

## Features

### Trending Props
See which props the community is betting on right now:
- **Player name** + **market** (points, rebounds, assists, yards, etc.)
- **Consensus direction** (over/under bias)
- **How many people** mentioned it
- **Where it's trending** (Reddit, Vegas, Discord)

### Filters
- **Time Period**: Last 24 hours, 7 days, or 30 days
- **Minimum Sources**: Only show props mentioned in multiple sources
- **Sport Filter**: See what's hot in NBA, NFL, MLB, NHL

### Anonymized
All data is aggregated and anonymized:
- No usernames or author identification
- Only statistics: mention counts, consensus direction
- Privacy-first design

## API Endpoints

### Get Trending Props
```
GET /insights/trending?time_filter=day&min_sources=1&min_mentions=2
```

**Parameters:**
- `time_filter`: `day` (24h), `week` (7d), `month` (30d)
- `min_sources`: Minimum # of sources that mention prop (1-3)
- `min_mentions`: Minimum # of mentions across all sources

**Response:**
```json
{
  "trending": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 12,
      "sources": ["reddit", "vegas"],
      "consensus_direction": "over",
      "over_consensus": 10,
      "under_consensus": 2,
      "mentions": [...]
    }
  ],
  "metadata": {...}
}
```

### Get Trending by Sport
```
GET /insights/trending/nba?time_filter=day
```

### Community Statistics
```
GET /insights/stats
```

Shows top 5 trending props and total unique props by time period.

## Discord Integration

Want to include your Discord community's picks?

### Setup
1. Create a Discord webhook in your betting Discord channel
2. Call the webhook endpoint:

```bash
curl -X POST "http://localhost:8000/insights/discord/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "LeBron over 25.5 points",
    "channel": "sharp-picks",
    "author": "sharp-bettor"
  }'
```

### Format
Discord messages are parsed for prop patterns:
- "Player Name over/under LINE stat"
- Examples:
  - "Luka over 27.5 points"
  - "Kelce u 60.5 yards"
  - "Betts over 1.5 home runs"

## How It Works

### Reddit Scraping
- Monitors r/sportsbooks, r/nba, r/nfl, r/mlb, r/nhl, r/sportsbetting
- Extracts props using regex patterns
- Looks for patterns like "Player over X.X points"
- Groups by player + market + line
- Shows consensus if 3+ people mention same prop

### Vegas Featured Props
- Integrates with existing DraftKings/FanDuel scraper data
- Shows which props sportsbooks are promoting
- Tracks line movement for sharp action signals
- (Future: Integration with props_dk_enhanced.py)

### Discord Monitoring
- Receives webhook messages from Discord
- Parses casual betting chat for props
- Aggregates with other sources
- Setup: Configure webhook URLs in system

## Privacy & Anonymization

✅ **What we collect:**
- Prop mentions (player name, line, over/under)
- Time of mention
- Source (Reddit/Vegas/Discord)

❌ **What we DON'T collect:**
- User accounts or Discord usernames (in aggregated view)
- Personal betting history
- Win/loss records per person
- Any identifying information

All data is aggregated only - you see statistics, not individuals.

## Examples

### Find the Hottest Picks This Week
```
GET /insights/trending?time_filter=week&min_sources=2&min_mentions=5
```
Shows props mentioned in at least 2 different sources, 5+ total mentions in the past week.

### Track NBA Props Today
```
GET /insights/trending/nba?time_filter=day
```
All trending NBA props from today.

### Quick Stats
```
GET /insights/stats
```
Quick overview of trending props across all time periods.

## Future Enhancements

- 📈 Line movement tracking (sharp vs public money)
- 🎯 Hit rate by source (which sources are most accurate?)
- 🔔 Alerts for consensus props
- 📊 Historical trending data
- ⭐ Trending streaks (props getting hotter)
- 🏆 Top bettors (anonymized leaderboard of most-mentioned picks)
