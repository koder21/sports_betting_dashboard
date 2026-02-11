# Game Details Page - Quick Start Guide

## 🚀 How to Access

### Method 1: From Live Scores Page
1. Navigate to "Live" (📊 Live Scores) in the sidebar
2. Find any game in the table
3. Click the **"📊 Details"** button on the right side of the row
4. You'll be taken to the game details page

### Method 2: Direct URL
Navigate directly to:
```
http://localhost:5173/games/{gameId}/details
```
Example:
```
http://localhost:5173/games/202502110020/details
```

### Method 3: From Code
```javascript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
navigate(`/games/${gameId}/details`);
```

## 📋 Page Layout

```
┌─ Top ──────────────────────────────────────────┐
│                                                │
│  Status Badge | Game Date | League             │
│                                                │
│  [ Team Logo ] Score        Score [ Team Logo ]│
│      vs                                        │
│  [ Time/Info ]    or    [ Final/Live Info ]   │
│                                                │
│  Period: Q2 | Clock: 5:34                     │
│                                                │
├─ Tabs ────────────────────────────────────────┤
│  📊 Overview | 📈 Statistics | 💰 My Bets (N) │
│                                                │
├─ Content Area ────────────────────────────────┤
│                                                │
│  (Dynamically changes based on selected tab)   │
│                                                │
│  [Overview / Stats Table / Bet Cards]          │
│                                                │
└────────────────────────────────────────────────┘
```

## 🎮 Interactive Elements

### Header Section
- **Team Cards**: Click or hover to see aggregated stats
- **Score**: Large, easy-to-read display
- **Status Badge**: Shows game state with color coding

### Tab Navigation
```
Click any tab to switch content:
  📊 Overview    → Summary team stats
  📈 Statistics  → Detailed player box score
  💰 My Bets     → Your bets with live tracking
```

### Statistics Tab
- **Team Toggle**: Switch between Home/Away teams
- **Hover Rows**: Player rows highlight on hover
- **Scroll**: Horizontally scroll on mobile for all stats
- **Sort**: Already sorted by points (descending)

### Bets Tab
- **Bet Cards**: Each card is independently styled
- **Live Performance**: Scroll down in card to see current stats
- **Status Colors**: Green (WIN), Red (LOSS), Blue (PENDING)
- **Expand**: Cards have hover effects showing more detail

## 📊 What Each Tab Shows

### 1. Overview Tab - Quick Summary
```
Home Team Stats          Away Team Stats
━━━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━━
Points:     104          Points:     98
Rebounds:    45          Rebounds:    42
Assists:     28          Assists:     25
Steals:      12          Steals:      10
Blocks:       8          Blocks:       7
```

**When to Use:**
- Quick glance at team performance
- Comparing teams side-by-side
- Understanding game flow at a glance

### 2. Statistics Tab - Detailed Box Score
```
┌────────────────────────────────────────────┐
│ Switch Team: [Home Team] [Away Team]       │
├────────────────────────────────────────────┤
│ Player          MIN PTS REB AST STL BLK TO │
├────────────────────────────────────────────┤
│ [👤] Jalen Brown 32  28  12   5  2  1  2  │
│ [👤] Jayson T.   35  25  11   8  1  0  3  │
│ [👤] Al Horford  28  12   8   6  0  2  1  │
│ ...                                        │
└────────────────────────────────────────────┘
```

**When to Use:**
- Viewing detailed player performance
- Checking specific player stats
- Analyzing shooting percentages
- Comparing player matchups

**Controls:**
- **Team Buttons**: Toggle between teams
- **Horizontal Scroll**: Scroll right to see FG%, 3PT%, FT%
- **Row Hover**: Rows highlight on hover for clarity

### 3. My Bets Tab - Live Bet Tracking
```
┌─────────────────────────┐  ┌─────────────────────────┐
│ ✓ WIN                   │  │ ⏱ PENDING               │
│ Spread: Celtics -4      │  │ Player Prop: Tatum      │
│ @1.95                   │  │ Over 25.5 PTS           │
│ Stake: $50              │  │ @1.90                   │
│ Profit: +$47.50         │  │ Stake: $25              │
│                         │  │                         │
│ 🎯 Live: Celtics 104    │  │ 🎯 Live Performance     │
│    vs LA Lakers 98      │  │ [👤] Jayson Tatum      │
│    (Cover -4 ✓)         │  │ Current: 25 PTS         │
└─────────────────────────┘  │ vs Over 25.5 (tracking) │
                             └─────────────────────────┘
```

**When to Use:**
- Tracking active bets on this game
- Monitoring player prop progress
- Seeing bet results
- Comparing expected vs actual performance

**Features:**
- **Status Color Coding**: Instant visual feedback
- **Live Performance**: Real-time player stats
- **Profit Display**: Shows +/- outcome
- **Raw Bet Text**: Original bet slip for reference

## 🎯 Common Tasks

### Task: Find a Specific Player's Stats
1. Click **"📈 Statistics"** tab
2. Use **team toggle** buttons to select correct team
3. **Scroll down** to find player (sorted by points)
4. Check all columns for stats

### Task: Check Your Bet Performance
1. Click **"💰 My Bets"** tab
2. Find your bet by type or player
3. Look for **"🎯 Live Performance"** section
4. See current vs target stat

### Task: Compare Teams
1. **Overview tab** shows quick comparison
2. For details, use **Statistics tab**
3. Switch teams using buttons
4. Compare key players and stats

### Task: Find Winning/Losing Bets
1. Click **"💰 My Bets"** tab
2. Look for **status badges**:
   - **✓ WIN** = Bet won
   - **✗ LOSS** = Bet lost
   - **⏱ PENDING** = Still active
3. Check **profit** amount for details

### Task: Check Game Status
1. Look at **status badge** at top:
   - **🔴 LIVE** = Game in progress
   - **✓ FINAL** = Game finished
   - **📅 UPCOMING** = Hasn't started
2. Check **period and clock** for live games
3. See **time/final info** in center divider

## 💡 Tips & Tricks

### 🔄 Refresh Data
- Page auto-refreshes when loaded
- For live games, manual refresh shows latest stats
- May need to wait for stats scraper to populate

### 📱 Mobile Usage
- Swipe table horizontally for all stats
- Tap team buttons to switch teams
- Cards stack vertically for easy reading
- All buttons remain easy to tap

### ⌨️ Keyboard Shortcuts
- None implemented yet, but all UI is tab-accessible
- Click any interactive element for access

### 🖱️ Hover Effects
- Hover over team cards → slight lift + color change
- Hover over player rows → row highlights
- Hover over bet cards → lifts up + shadow expands
- Hover over buttons → color change + shadow

### 🌙 Dark Theme
- Page uses dark theme throughout
- All text white/light for readability
- Cyan accent (#00d4ff) for key elements
- Green for wins, red for losses

## ⚠️ Known Limitations

| Limitation | Workaround |
|-----------|-----------|
| No real-time updates | Manually refresh page |
| Need player stats populated | Run stats scraper first |
| Stats only as recent as scraper | Check scraper schedule |
| No historical comparison | View other games for reference |
| No play-by-play yet | Use parent gameId for intel |

## 🔍 What Data Shows

### Player Stats Available
**Basketball:**
- Minutes, Points, Rebounds, Assists, Steals, Blocks, Turnovers
- Field Goal %, 3-Point %, Free Throw %

**Football:**
- Passing: Yards, TDs, INTs
- Rushing: Yards, TDs
- Receiving: Yards, TDs, Targets
- Defense: Tackles, Sacks

**Hockey:**
- Goals, Assists, Shots, Hits, Blocks
- +/-, Saves (for goalies)

**Baseball:**
- Hits, Runs, RBIs, Home Runs, Stolen Bases
- Strikeouts, Walks
- Pitching: IP, K, BB, ER

**Soccer:**
- Goals, Assists, Shots on Target
- Passes, Tackles, Saves (for goalies)

### Bet Information Shown
- **Bet Type**: spread, moneyline, over_under, player_prop, etc.
- **Market**: Specific betting line or prop
- **Selection**: What you picked (team, total, player, etc.)
- **Stake**: How much you wagered
- **Odds**: Betting odds at time of placement
- **Status**: pending, win, loss, void
- **Profit**: +/- amount from bet
- **Live Performance**: For player props, current stat value

## 🎨 Visual Indicators

### Status Badges
```
🔴 LIVE     - Game in progress (red, pulsing)
✓ FINAL     - Game finished (green)
📅 UPCOMING - Game hasn't started (cyan)
```

### Bet Status
```
✓ WIN       - Bet was successful (green)
✗ LOSS      - Bet failed (red)
⏱ PENDING   - Awaiting result (cyan)
○ VOID      - Bet cancelled (gray)
```

### Performance Indicators
```
🎯 Live Performance - Shows real-time player stats
$47.50 (green)     - Winning bet profit
-$25.00 (red)      - Losing bet loss
$0.00 (gray)       - Break even
```

## 📞 Support

### If Something Doesn't Work

1. **Check the Console**
   - Open browser DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for API failures

2. **Verify Data Exists**
   ```sql
   -- Check if game exists
   SELECT * FROM games WHERE game_id = '...';
   
   -- Check if player stats exist
   SELECT COUNT(*) FROM player_stats WHERE game_id = '...';
   
   -- Check if bets exist
   SELECT * FROM bets WHERE game_id = '...';
   ```

3. **Common Issues**
   - No stats shown: PlayerStats not populated yet
   - Missing logos: Team.logo field is empty
   - No player pics: Player.headshot field is empty
   - Bets not showing: Check game_id matches in Bet table

4. **For Help**
   - Check backend logs for API errors
   - Verify database connection
   - Ensure scrapers are running
   - Check timezone settings

## 🎉 Enjoy!

You now have a professional, ESPN-style game details page with live bet tracking. Use it to:
- ✅ Monitor your bets in real-time
- ✅ Track player performance against your props
- ✅ Analyze team and individual statistics
- ✅ Make informed decisions on future bets
- ✅ Review game details after completion

Happy betting! 🎲
