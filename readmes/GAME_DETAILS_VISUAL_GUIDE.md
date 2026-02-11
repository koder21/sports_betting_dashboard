# Game Details Page - Visual Architecture & Feature Guide

## 🎯 Feature Summary

A comprehensive, ESPN-style game details page with **live bet tracking** and **player statistics**.

## 📊 Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│                   GAME DETAILS PAGE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔴 LIVE | Feb 11, 2025 | NBA                             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              GAME SCORE & INFO                       │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │  [🏀] Boston Celtics         [🏀] Los Angeles Lakers  │ │
│  │         104                                  98       │ │
│  │                   vs                                  │ │
│  │         Stats Summary                 Stats Summary   │ │
│  │  PTS: 104  REB: 45  AST: 28    PTS: 98  REB: 42  AST │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
├─ TABS ──────────────────────────────────────────────────────┤
│  📊 Overview  │  📈 Statistics  │  💰 My Bets (3)          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TAB CONTENT (dynamic based on selected tab)                │
│                                                             │
│  OVERVIEW:                                                  │
│  ┌─────────────────────┬─────────────────────┐             │
│  │  Boston Celtics     │  LA Lakers          │             │
│  ├─────────────────────┼─────────────────────┤             │
│  │ Points:       104   │ Points:        98   │             │
│  │ Rebounds:      45   │ Rebounds:       42  │             │
│  │ Assists:       28   │ Assists:        25  │             │
│  │ Steals:        12   │ Steals:         10  │             │
│  │ Blocks:         8   │ Blocks:          7  │             │
│  └─────────────────────┴─────────────────────┘             │
│                                                             │
│  STATISTICS:                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Player Stats Table                                  │   │
│  ├──────────┬──────┬─────┬─────┬─────┬─────┬───────────┤   │
│  │ Player   │ MIN  │ PTS │ REB │ AST │ FG  │ 3PT │ FT   │   │
│  ├──────────┼──────┼─────┼─────┼─────┼─────┼───────────┤   │
│  │[👤] Jalen Brown  32  28   12    5   10-18  4-8  4-5  │   │
│  │[👤] Jayson Tatum 35  25   11    8   9-19   2-5  5-7  │   │
│  │[👤] Al Horford   28  12   8     6   5-10   1-2  1-2  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  MY BETS:                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐       │
│  │ ✓ WIN               │  │ ⏱ PENDING            │       │
│  │                      │  │                      │       │
│  │ Spread: Celtics -4  │  │ Player Prop: Tatum   │       │
│  │ @1.95               │  │ Over 25.5 PTS        │       │
│  │ $50 → +$47.50       │  │ @1.90                │       │
│  │                      │  │ $25 (pending)        │       │
│  │ 🎯 Live: 25 PTS     │  │                      │       │
│  │    vs Over 24.5     │  │ 🎯 Live: 25 PTS      │       │
│  └──────────────────────┘  │    (tracking...)     │       │
│                            └──────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features

### 1. **Live Score Display**
- Team logos and names
- Large, readable score
- Status badge (LIVE, FINAL, UPCOMING)
- Game time/date information
- Live period and clock

### 2. **Three Information Tabs**

#### 📊 Overview Tab
- Side-by-side team stat comparison
- Shows: Points, Rebounds, Assists, Steals, Blocks
- Quick snapshot of team performance

#### 📈 Statistics Tab
- Full box score for each team
- Player-by-player statistics
- Sortable by different stats
- Shows:
  - Player name, number, position
  - Headshot photo
  - Minutes played
  - Points, Rebounds, Assists
  - Steals, Blocks, Turnovers
  - Field Goal percentages (FG, 3PT, FT)

#### 💰 My Bets Tab
- Shows all bets placed on this game
- Individual bet cards with:
  - **Bet Status**: WIN, LOSS, PENDING, VOID
  - **Bet Info**: Type, Market, Selection, Odds
  - **Stake & Profit**: Amount wagered and result
  - **Live Performance**: For player props, shows current player stats
  
### 3. **Live Bet Tracking** ⭐
For player prop bets (e.g., "Jayson Tatum Over 25.5 PTS"):
- Shows player headshot and name
- Displays current stat value
- Updates as game progresses
- Color-coded by performance

**Example:**
```
🎯 Live Performance
[👤 Photo] Jayson Tatum
    #0
Over 25.5 PTS  →  Current: 25 PTS
```

## 🎨 Design System

### Color Palette
```
Primary Accent:    #00d4ff (Cyan)
Success:          #22c155 (Green - for wins)
Danger:           #ff6b6b (Red - for losses)
Pending:          #00d4ff (Blue - for pending)
Background:       Dark blue gradients
Text:             White/Light gray
```

### Styling Features
- **Glassmorphism**: Semi-transparent cards with blur effects
- **Animations**: Smooth transitions, pulse effects on live badges
- **Hover Effects**: Cards lift up, shadows expand
- **Responsive**: Works on desktop, tablet, mobile

## 📱 Responsive Design

```
Desktop (1400px+)
  ├─ Full 2-column team stats layout
  ├─ Multi-column player stats table
  └─ 3-column bet card grid

Tablet (1024px)
  ├─ Single column team stats
  ├─ Responsive player table
  └─ 1-2 column bet cards

Mobile (768px)
  ├─ Stacked team info
  ├─ Horizontal scrolling stats table
  └─ Single column bet cards
```

## 🔄 Data Flow

```
User clicks "📊 Details" button
         ↓
Navigate to /games/{gameId}/details
         ↓
GameDetailPage component loads
         ↓
Fetches: GET /games/{gameId}/detailed
         ↓
Backend endpoint:
  ├─ Fetches Game record
  ├─ Gets GameUpcoming/GameLive/GameResult status
  ├─ Fetches all PlayerStats for game
  ├─ Aggregates team stats
  ├─ Fetches all Bets on game
  ├─ Enriches bets with current player performance
  └─ Returns complete data
         ↓
Frontend renders:
  ├─ Header with scores
  ├─ Three tabs with content
  └─ Live performance tracking on bets
         ↓
User can:
  ├─ View team statistics
  ├─ Check player box scores
  ├─ Track bets in real-time
  └─ See how their player props are performing
```

## 💡 Usage Scenarios

### Scenario 1: Watching a Game
1. Game is live, user wants details
2. Click "📊 Details" from live scores
3. See real-time score and team stats
4. Click "📈 Statistics" to see player performance
5. Click "💰 My Bets" to track your prop bets

### Scenario 2: Checking a Finished Game
1. Game is final
2. Click "📊 Details" to see final scores
3. View full box scores and statistics
4. See which bets won/lost
5. Review live performance of your player props

### Scenario 3: Analyzing Before Betting
1. Game is upcoming
2. Click "📊 Details" to see preview
3. Review previous season stats (if available)
4. Check team/player information
5. Make informed betting decisions

## 🔌 API Integration

### Endpoint: `GET /games/{gameId}/detailed`

**Request:**
```
GET /api/games/202502110020/detailed
```

**Response Structure:**
```json
{
  "game": {
    "game_id": "string",
    "sport": "NBA",
    "status": "live",
    "start_time": "2025-02-11T20:30:00Z",
    "home": {
      "team_name": "Boston Celtics",
      "logo": "url",
      "score": 104,
      "stats": { "points": 104, "rebounds": 45, ... }
    },
    "away": { ... }
  },
  "home_players": [ { player stats } ],
  "away_players": [ { player stats } ],
  "bets": [
    {
      "id": 123,
      "bet_type": "spread",
      "selection": "Celtics -4",
      "status": "win",
      "current_performance": null
    },
    {
      "id": 124,
      "bet_type": "player_prop",
      "selection": "Tatum Over 25.5 PTS",
      "status": "pending",
      "current_performance": {
        "player_name": "Jayson Tatum",
        "stat_display": "25 PTS",
        "headshot": "url"
      }
    }
  ]
}
```

## ✨ Special Features

### Live Badge Animation
When game is live, the status badge pulses:
```css
animation: pulse 2s infinite;
```

### Score Flash Effect
When score changes, flash the score:
```css
animation: flash 0.3s ease-out;
```

### Hover Effects
Cards respond to hover:
- Lift up (translateY)
- Increase shadow
- Change border color

### Responsive Tables
Player stats tables:
- Sticky header that stays visible when scrolling
- Horizontal scrolling on mobile
- Highlighted key stats (PTS column in cyan)

## 🎯 Next Steps

To fully leverage this feature:

1. **Ensure Player Stats are Populated**
   - Run the PlayerStatsScraper
   - Check: `SELECT COUNT(*) FROM player_stats;`

2. **Verify Team Logos**
   - Update Team table with logo URLs
   - Check: `SELECT logo FROM teams LIMIT 5;`

3. **Verify Player Headshots**
   - Update Player table with headshot URLs
   - Check: `SELECT headshot FROM players LIMIT 5;`

4. **Test All Sports**
   - NBA, NFL, NHL, MLB, Soccer
   - Verify stats display correctly for each

5. **Monitor Performance**
   - Check for slow queries
   - Optimize if needed

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No player stats showing | Check PlayerStats table population |
| Missing team logos | Update Team.logo field |
| No headshots | Update Player.headshot field |
| Slow page load | Optimize database queries |
| Bets not showing | Verify game_id in Bet table |
| Stats not matching | Check if sports type is mapped correctly |

## 📈 Performance Metrics

Expected load times:
- Page load: < 500ms
- Data fetch: < 1s
- Tab switch: < 100ms
- Responsive at 60fps

## 🚦 Status Indicators

```
LIVE (Red pulse):    Game actively being played
FINAL (Green):       Game completed
UPCOMING (Cyan):     Game hasn't started yet

Bet Status:
✓ WIN (Green):       Bet won
✗ LOSS (Red):        Bet lost
⏱ PENDING (Cyan):    Awaiting result
○ VOID (Gray):       Bet voided
```

## 📝 Notes

- All timestamps are converted to user's timezone
- Player stats aggregated server-side for performance
- Bets with null player_id (team/total bets) won't show live performance
- Responsive design tested on major devices
- Accessibility features included (alt text, semantic HTML)
