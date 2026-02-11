# Community Insights - Architecture & Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMUNITY DATA SOURCES                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔴 REDDIT              📊 VEGAS            💬 DISCORD      │
│  ─────────────────────  ─────────────────  ─────────────────│
│  • r/sportsbooks       • Featured props    • Webhooks       │
│  • r/nba               • Line movements    • Bot messages    │
│  • r/nfl               • Sharp action      • Chat parsing    │
│  • r/mlb               • Odds trends       • User picks      │
│  • r/nhl               • Sportsbook data   • Group chats     │
│  • r/nhl                                                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    COMMUNITY INSIGHTS SERVICE                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Data Collection                                          │
│     • Reddit Scraper (Pushshift API)                        │
│     • Vegas Props Aggregator                                │
│     • Discord Webhook Receiver                              │
│                                                               │
│  2. Prop Extraction                                         │
│     • Regex pattern matching                                │
│     • Player name normalization                             │
│     • Market type classification                            │
│     • Line parsing & direction detection                    │
│                                                               │
│  3. Aggregation                                             │
│     • Group by player + market + line                       │
│     • Count mentions per source                             │
│     • Calculate consensus direction                         │
│     • Filter by thresholds                                  │
│                                                               │
│  4. Ranking                                                 │
│     • Sort by source diversity                              │
│     • Sort by mention count                                 │
│     • Return top trending                                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    API ENDPOINTS                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  GET /insights/trending                                     │
│      ├─ time_filter: day|week|month                        │
│      ├─ min_sources: 1-3                                    │
│      └─ min_mentions: integer                               │
│                                                               │
│  GET /insights/trending/{sport}                            │
│      ├─ sport: nba|nfl|mlb|nhl                             │
│      └─ time_filter: day|week|month                        │
│                                                               │
│  POST /insights/discord/webhook                            │
│      ├─ message: prop text                                  │
│      ├─ channel: channel name                               │
│      └─ author: user name                                   │
│                                                               │
│  GET /insights/stats                                        │
│      └─ Returns summary across time periods                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND DISPLAY                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  CommunityInsights Component                                │
│  ├─ Time period selector                                    │
│  ├─ Sport filter                                            │
│  ├─ Source filter                                           │
│  └─ Trending props cards                                    │
│     ├─ Player name & market                                 │
│     ├─ Consensus (Over/Under)                               │
│     ├─ Vote counts                                          │
│     ├─ Mention total                                        │
│     └─ Source indicators                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Scenario: "LeBron over 25.5 points" trends

```
1. EXTRACTION
   ┌─ Reddit Post: "LeBron over 25.5 points is 🔥"
   ├─ Vegas: Features "LeBron O 25.5" with high action
   └─ Discord: "#sharp-picks: LeBron over 25.5"
   
                        ↓
2. PARSING
   ├─ Player: "LeBron James" → normalized
   ├─ Market: "points" → canonical name
   ├─ Line: 25.5
   ├─ Direction: "over"
   └─ Source: ["reddit", "vegas", "discord"]
   
                        ↓
3. AGGREGATION
   ├─ Key: "lebron james|points|25.5"
   ├─ Mentions: [reddit_mention, vegas_mention, discord_mention]
   ├─ Total count: 3
   └─ Sources: 3 different sources
   
                        ↓
4. RANKING & FILTERING
   ├─ Meets minimum sources? ✓ (3 >= 1)
   ├─ Meets minimum mentions? ✓ (3 >= 2)
   ├─ Consensus direction? "over" (all 3 mention over)
   └─ Rank score: High (3 sources + 3 mentions)
   
                        ↓
5. API RESPONSE
   {
     "player_name": "Lebron James",
     "market": "points",
     "line": 25.5,
     "total_mentions": 3,
     "sources": ["reddit", "vegas", "discord"],
     "source_count": 3,
     "consensus_direction": "over",
     "over_consensus": 3,
     "under_consensus": 0
   }
   
                        ↓
6. FRONTEND DISPLAY
   ┌──────────────────────────────┐
   │  LeBron James (points)        │
   │  Line: 25.5                   │
   │  ⬆️ OVER (3 votes)           │
   │  💬 3 mentions                │
   │  🔴 Reddit | 📊 Vegas | 💬   │
   └──────────────────────────────┘
```

## Data Processing Flow

### Reddit Scraping
```
Request
  ↓
Pushshift API (100 posts per subreddit)
  ↓
Filter for betting keywords (over, under, props, pick)
  ↓
Regex extract: "Player Name (O|U|over|under) LINE STAT"
  ↓
Normalize player names & stat types
  ↓
Return parsed props
```

### Vegas Props
```
Request
  ↓
Query props scraper data (props_dk_enhanced.py)
  ↓
Find featured/promoted props
  ↓
Track line movement history
  ↓
Identify high-action props
  ↓
Return Vegas featured props
```

### Discord Webhooks
```
POST /insights/discord/webhook
  ↓
Extract message text
  ↓
Regex parse for prop patterns
  ↓
Normalize & categorize
  ↓
Store with channel & author info
  ↓
Aggregate with other sources
```

## Aggregation Logic

```
For each unique prop:
  
  1. Collect all mentions
     mentions = [
       {source: "reddit", direction: "over", ...},
       {source: "vegas", direction: "over", ...},
       {source: "discord", direction: "under", ...}
     ]
  
  2. Count sources
     unique_sources = {"reddit", "vegas", "discord"} → 3 sources
  
  3. Count directions
     over_consensus = 2
     under_consensus = 1
     consensus = "over"
  
  4. Apply filters
     if len(sources) >= min_sources AND len(mentions) >= min_mentions:
       include in trending
  
  5. Sort by
     PRIMARY: source_count (DESC) - more sources = better signal
     SECONDARY: mention_count (DESC) - more mentions = more popular
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Reddit scrape (1 subreddit) | 2-5s | Pushshift API |
| Vegas props query | <1s | Database query |
| Discord webhook | <50ms | Simple parsing |
| Aggregation | <100ms | In-memory grouping |
| **Total API response** | **3-6s** | First request slower |

**Optimization opportunities:**
- Cache trending results (5-10 min TTL)
- Background scraping on scheduler
- Async Reddit scraping (all subs in parallel)
- Store historical data for trending velocity

## Filtering Example

Query: `GET /insights/trending?time_filter=day&min_sources=2&min_mentions=3`

```
All props from last 24h: 200 props
  ↓
Filter: min_sources=2 (only if 2+ different sources)
  → 85 props remain
  ↓
Filter: min_mentions=3 (only if 3+ total mentions)
  → 42 props remain
  ↓
Sort by source_count DESC, then mention_count DESC
  ↓
Return top 50 trending
```

## Consensus Direction Logic

```
If over_count > under_count:
  direction = "over"
Elif under_count > over_count:
  direction = "under"
Else:
  direction = "mixed"

Example:
  Over votes: 7
  Under votes: 2
  → Direction: "over" (consensus)
  
  Over votes: 5
  Under votes: 5
  → Direction: "mixed" (disagreement)
```

## Future Enhancements

### Phase 2
- 📈 **Line Movement Tracking** - Detect sharp money
- 🎯 **Hit Rate Analytics** - Which sources are most accurate?
- 🔔 **Consensus Alerts** - Notify when props reach threshold
- ⭐ **Trending Velocity** - Props gaining momentum

### Phase 3
- 📊 **Historical Database** - Track trending over time
- 🏆 **Sharp Bettor Rankings** - Leaderboard of best picks
- 🔗 **Cross-source Validation** - When multiple sources align
- 💰 **EV Calculation** - Calculate expected value vs market

### Phase 4
- 🤖 **ML Model Integration** - Predict prop success
- 🌐 **Advanced Scraping** - X/Twitter, Telegram, blogs
- 📱 **Push Notifications** - Alert on trending props
- 🔐 **User Preferences** - Personalized trending feed
