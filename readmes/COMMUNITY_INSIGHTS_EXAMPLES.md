# Community Insights - API Response Examples

## Example 1: Get Trending Props (All Sources)

### Request
```bash
curl "http://localhost:8000/insights/trending?time_filter=day&min_sources=1&min_mentions=2"
```

### Response
```json
{
  "trending": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 12,
      "sources": ["reddit", "vegas"],
      "source_count": 2,
      "over_consensus": 10,
      "under_consensus": 2,
      "consensus_direction": "over",
      "mentions": [
        {
          "player_name": "Luka Doncic",
          "market": "points",
          "line": 27.5,
          "direction": "over",
          "source": "reddit",
          "subreddit": "sportsbooks",
          "mentioned_at": "2026-02-09T15:30:45.123456"
        },
        {
          "player_name": "Luka Doncic",
          "market": "points",
          "line": 27.5,
          "direction": "over",
          "source": "vegas",
          "mentioned_at": "2026-02-09T15:25:00.000000"
        }
      ]
    },
    {
      "player_name": "Travis Kelce",
      "market": "receiving_yards",
      "line": 60.5,
      "total_mentions": 8,
      "sources": ["reddit", "discord"],
      "source_count": 2,
      "over_consensus": 5,
      "under_consensus": 3,
      "consensus_direction": "over",
      "mentions": [
        {
          "player_name": "Travis Kelce",
          "market": "receiving_yards",
          "line": 60.5,
          "direction": "over",
          "source": "reddit",
          "subreddit": "nfl",
          "mentioned_at": "2026-02-09T14:45:30.000000"
        },
        {
          "player_name": "Travis Kelce",
          "market": "receiving_yards",
          "line": 60.5,
          "direction": "under",
          "source": "discord",
          "channel": "sharp-picks",
          "author": "bettor123",
          "mentioned_at": "2026-02-09T14:32:15.000000"
        }
      ]
    },
    {
      "player_name": "Jayson Tatum",
      "market": "rebounds",
      "line": 6.5,
      "total_mentions": 7,
      "sources": ["reddit"],
      "source_count": 1,
      "over_consensus": 5,
      "under_consensus": 2,
      "consensus_direction": "over",
      "mentions": [...]
    }
  ],
  "total_unique_props": 3,
  "metadata": {
    "time_filter": "day",
    "updated_at": "2026-02-09T16:00:00.000000",
    "min_sources": 1,
    "min_mentions": 2,
    "sources": ["reddit", "vegas", "discord"]
  }
}
```

---

## Example 2: Get NBA Trending Props

### Request
```bash
curl "http://localhost:8000/insights/trending/nba?time_filter=day"
```

### Response
```json
{
  "trending": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 8,
      "sources": ["reddit"],
      "source_count": 1,
      "over_consensus": 7,
      "under_consensus": 1,
      "consensus_direction": "over",
      "mentions": [...]
    },
    {
      "player_name": "Stephen Curry",
      "market": "three_pt",
      "line": 4.5,
      "total_mentions": 6,
      "sources": ["reddit"],
      "source_count": 1,
      "over_consensus": 4,
      "under_consensus": 2,
      "consensus_direction": "over",
      "mentions": [...]
    },
    {
      "player_name": "Jayson Tatum",
      "market": "points",
      "line": 26.5,
      "total_mentions": 5,
      "sources": ["reddit"],
      "source_count": 1,
      "over_consensus": 3,
      "under_consensus": 2,
      "consensus_direction": "over",
      "mentions": [...]
    }
  ],
  "total_unique_props": 3,
  "metadata": {
    "time_filter": "day",
    "updated_at": "2026-02-09T16:00:00.000000",
    "min_sources": 1,
    "min_mentions": 2,
    "sources": ["reddit", "vegas", "discord"]
  }
}
```

---

## Example 3: Get Statistics

### Request
```bash
curl "http://localhost:8000/insights/stats"
```

### Response
```json
{
  "summary": {
    "last_24h": 23,
    "last_7d": 87,
    "last_30d": 245
  },
  "top_trending_24h": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 12,
      "sources": ["reddit", "vegas"],
      "source_count": 2,
      "consensus_direction": "over"
    },
    {
      "player_name": "Travis Kelce",
      "market": "receiving_yards",
      "line": 60.5,
      "total_mentions": 8,
      "sources": ["reddit", "discord"],
      "source_count": 2,
      "consensus_direction": "over"
    },
    {
      "player_name": "Jayson Tatum",
      "market": "rebounds",
      "line": 6.5,
      "total_mentions": 7,
      "sources": ["reddit"],
      "source_count": 1,
      "consensus_direction": "over"
    },
    {
      "player_name": "Stephen Curry",
      "market": "three_pt",
      "line": 4.5,
      "total_mentions": 6,
      "sources": ["reddit"],
      "source_count": 1,
      "consensus_direction": "over"
    },
    {
      "player_name": "Patrick Mahomes",
      "market": "passing_yards",
      "line": 275.5,
      "total_mentions": 5,
      "sources": ["reddit"],
      "source_count": 1,
      "consensus_direction": "over"
    }
  ],
  "sources": ["reddit", "vegas", "discord"]
}
```

---

## Example 4: Process Discord Webhook

### Request
```bash
curl -X POST "http://localhost:8000/insights/discord/webhook" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Luka+over+27.5+points&channel=sharp-picks&author=bettor123"
```

### Response
```json
{
  "status": "processed",
  "props_extracted": 1,
  "props": [
    {
      "player_name": "Luka",
      "market": "points",
      "line": 27.5,
      "direction": "over",
      "source": "discord",
      "channel": "sharp-picks",
      "author": "bettor123",
      "mentioned_at": "2026-02-09T16:05:30.000000"
    }
  ]
}
```

---

## Example 5: Filter by Minimum Sources

### Request (Only show props from 2+ sources)
```bash
curl "http://localhost:8000/insights/trending?time_filter=day&min_sources=2&min_mentions=2"
```

### Response
```json
{
  "trending": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 12,
      "sources": ["reddit", "vegas"],
      "source_count": 2,
      "over_consensus": 10,
      "under_consensus": 2,
      "consensus_direction": "over",
      "mentions": [...]
    },
    {
      "player_name": "Travis Kelce",
      "market": "receiving_yards",
      "line": 60.5,
      "total_mentions": 8,
      "sources": ["reddit", "discord"],
      "source_count": 2,
      "over_consensus": 5,
      "under_consensus": 3,
      "consensus_direction": "over",
      "mentions": [...]
    }
  ],
  "total_unique_props": 2,
  "metadata": {
    "time_filter": "day",
    "updated_at": "2026-02-09T16:00:00.000000",
    "min_sources": 2,
    "min_mentions": 2,
    "sources": ["reddit", "vegas", "discord"]
  }
}
```

---

## Example 6: Get Weekly Trending (Consensus Props)

### Request
```bash
curl "http://localhost:8000/insights/trending?time_filter=week&min_sources=2&min_mentions=5"
```

### Response (Shows only high-consensus props)
```json
{
  "trending": [
    {
      "player_name": "Luka Doncic",
      "market": "points",
      "line": 27.5,
      "total_mentions": 47,
      "sources": ["reddit", "vegas"],
      "source_count": 2,
      "over_consensus": 42,
      "under_consensus": 5,
      "consensus_direction": "over",
      "mentions": [...]
    },
    {
      "player_name": "Stephen Curry",
      "market": "three_pt",
      "line": 4.5,
      "total_mentions": 38,
      "sources": ["reddit", "discord"],
      "source_count": 2,
      "over_consensus": 30,
      "under_consensus": 8,
      "consensus_direction": "over",
      "mentions": [...]
    }
  ],
  "total_unique_props": 2,
  "metadata": {
    "time_filter": "week",
    "updated_at": "2026-02-09T16:00:00.000000",
    "min_sources": 2,
    "min_mentions": 5,
    "sources": ["reddit", "vegas", "discord"]
  }
}
```

---

## Response Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `player_name` | string | Normalized player name |
| `market` | string | Stat type (points, rebounds, assists, etc.) |
| `line` | float | The over/under line |
| `total_mentions` | integer | Total mentions across all sources |
| `sources` | array | Which sources mentioned it (reddit, vegas, discord) |
| `source_count` | integer | Number of different sources |
| `over_consensus` | integer | How many mentions were for over |
| `under_consensus` | integer | How many mentions were for under |
| `consensus_direction` | string | The consensus (over, under, or mixed) |
| `mentions` | array | Individual mention objects with source details |

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success - props returned |
| 400 | Bad request - invalid filter parameters |
| 500 | Server error - scraping or database issue |

---

## Query Parameter Guide

### time_filter
- `day` - Last 24 hours (default)
- `week` - Last 7 days
- `month` - Last 30 days

### min_sources
- `1` - Show props from any source (default)
- `2` - Show props mentioned in 2+ different sources
- `3` - Show props mentioned in all sources (high confidence)

### min_mentions
- `1` - Show props with 1+ mention
- `2` - Show props with 2+ mentions (default)
- `5` - Show only popular props with 5+ mentions
- etc.

---

## Usage Patterns

### Get hottest props (requires agreement)
```bash
GET /insights/trending?time_filter=day&min_sources=2&min_mentions=5
```

### Get all trending (less filtering)
```bash
GET /insights/trending?time_filter=week&min_sources=1&min_mentions=2
```

### Monitor specific sport
```bash
GET /insights/trending/nba?time_filter=day
GET /insights/trending/nfl?time_filter=day
```

### Get quick stats
```bash
GET /insights/stats
```

### Process Discord pick
```bash
POST /insights/discord/webhook?channel=picks&author=user&message=Player+over+Line
```
