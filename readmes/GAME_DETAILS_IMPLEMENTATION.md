# Game Details Page - Complete Implementation

## Overview
This feature provides a comprehensive, ESPN-style game details page that displays:
- **Live Game Score & Status** with real-time updates
- **Team Statistics** with aggregated stats (points, rebounds, assists, etc.)
- **Player Box Scores** with individual player performance stats
- **Live Bet Tracking** showing your bets on the game with current player performance
- **Multi-tab Navigation** for Overview, Statistics, and Your Bets

## Architecture

### Backend Changes

#### New API Endpoint: `GET /games/{game_id}/detailed`

Located in: `backend/routers/games.py` (lines 738-1000)

**Response Structure:**
```json
{
  "game": {
    "game_id": "string",
    "sport": "NBA|NFL|NHL|MLB|etc",
    "league": "string",
    "status": "upcoming|live|final",
    "start_time": "ISO 8601 datetime",
    "venue": "string",
    "period": "string",
    "clock": "string",
    "home": {
      "team_id": "string",
      "team_name": "string",
      "logo": "url",
      "score": "number",
      "stats": {
        "points": "number",
        "rebounds": "number",
        "assists": "number",
        "steals": "number",
        "blocks": "number"
      }
    },
    "away": { /* same structure */ }
  },
  "home_players": [
    {
      "player_id": "string",
      "player_name": "string",
      "jersey": "number",
      "position": "string",
      "headshot": "url",
      "minutes": "string",
      "points": "number",
      "rebounds": "number",
      "assists": "number",
      "steals": "number",
      "blocks": "number",
      "turnovers": "number",
      "fg": "string",      // "25-45"
      "three_pt": "string", // "5-12"
      "ft": "string",      // "8-10"
      "fouls": "number",
      "passing_yards": "number",
      "passing_tds": "number",
      "rushing_yards": "number",
      "receiving_yards": "number",
      "tackles": "number",
      "sacks": "number"
    }
  ],
  "away_players": [ /* same structure */ ],
  "bets": [
    {
      "id": "number",
      "placed_at": "ISO 8601 datetime",
      "bet_type": "spread|moneyline|over_under|player_prop|etc",
      "market": "string",
      "selection": "string",
      "stat_type": "string",
      "player_name": "string",
      "stake": "number",
      "odds": "number",
      "status": "pending|win|loss|void",
      "profit": "number or null",
      "result_value": "number or null",
      "raw_text": "string",
      "current_performance": {
        "player_id": "string",
        "player_name": "string",
        "stat_value": "number or null",
        "stat_display": "string",  // "15 PTS", "8 AST", etc
        "team_id": "string",
        "headshot": "url",
        "jersey": "number"
      }
    }
  ],
  "total_bets": "number"
}
```

**Features:**
- Fetches game from all three states (GameUpcoming, GameLive, GameResult)
- Aggregates player stats by team
- Calculates team totals for all relevant statistics
- Enriches bets with current player performance data
- Maps stat_type to actual player statistics (e.g., "Player PTS" → player.points)
- Supports all major sports (NBA, NFL, NHL, MLB, etc.)

### Frontend Changes

#### 1. New Page Component: `GameDetailPage.jsx`

Located in: `frontend/src/pages/GameDetailPage.jsx`

**Components:**
- `GameDetailPage` - Main container
- `PlayerStatsTable` - Renders team player statistics in table format
- `BetCard` - Individual bet card with live performance tracking

**Features:**
- Three tabs: Overview, Statistics, Bets
- Responsive design for mobile and desktop
- Live performance tracking for player prop bets
- Status badges (LIVE, FINAL, UPCOMING)
- Animated score displays
- Team comparison stats

#### 2. Styling: `GameDetailPage.css`

Located in: `frontend/src/pages/GameDetailPage.css`

**Design System:**
- Dark theme with cyan accent color (#00d4ff)
- Glassmorphism effects (backdrop-filter blur)
- Smooth transitions and animations
- ESPN-style professional appearance
- Responsive grid layouts

**Key Sections:**
- Header with score display and team logos
- Team stats comparison cards
- Player statistics table with scrolling
- Bet tracking cards with live performance
- Status badges with animations

#### 3. Button Integration: `LiveScoresPage.jsx`

Added "📊 Details" button to each game row that navigates to the detailed view.

**Changes:**
- Added `action-cell` with Details button
- Button uses `e.stopPropagation()` to prevent row click conflict
- Styled with gradient background and hover effects

#### 4. Routing: `App.jsx`

Added route: `/games/:gameId/details`

Maps to `GameDetailPage` component

#### 5. Styling: `styles.css`

Added `.details-btn` styling with:
- Gradient background (#00d4ff to #0099cc)
- Hover transform and shadow effects
- Active state styling

## Usage

### Accessing the Page

1. **From Live Scores**: Click the "📊 Details" button on any game row
2. **Direct URL**: Navigate to `/games/{gameId}/details`
3. **Link**: Use `navigate('/games/{gameId}/details')`

### User Interface

**Header Section:**
- Status badge (LIVE, FINAL, UPCOMING) with appropriate color
- Game date, sport, and league
- Team logos, names, and scores in large text
- Live/Final/Time information in center divider
- Period and clock for live games

**Overview Tab:**
- Side-by-side team stat cards
- Shows: Points, Rebounds, Assists, Steals, Blocks
- Clean, scannable format

**Statistics Tab:**
- Toggle between Home/Away team players
- Full box score table with columns:
  - Player info (name, jersey, position, headshot)
  - MIN, PTS, REB, AST, STL, BLK, TO
  - FG, 3PT, FT percentages
- Sorted by points (descending)
- Responsive scrolling on mobile

**Bets Tab:**
- Grid layout of bet cards
- Each card shows:
  - Bet status badge (WIN, LOSS, PENDING)
  - Bet type and market
  - Selection and stake
  - Profit/Loss
  - **Live Performance** section (for player props):
    - Player headshot and name
    - Current stat value (e.g., "15 PTS")
    - Jersey number
- Color coding by status (green=win, red=loss, blue=pending)
- Raw bet text for reference

## Data Mapping

### Sport-Specific Stats

The endpoint automatically detects sport type and includes relevant stats:

**Basketball (NBA, NCAAB):**
- minutes, points, rebounds, assists, steals, blocks
- turnovers, fouls
- fg (field goals), three_pt (3-pointers), ft (free throws)

**Football (NFL):**
- passing_yards, passing_tds, interceptions
- rushing_yards, rushing_tds
- receiving_yards, receiving_tds, receiving_ats (targets)
- tackles, sacks, forced_fumbles

**Hockey (NHL):**
- nhl_goals, nhl_assists, nhl_shots
- nhl_hits, nhl_blocks, nhl_plus_minus
- goalie_saves, goalie_ga, goalie_sv_pct

**Baseball (MLB):**
- hits, runs, rbi, hr (home runs), sb (stolen bases)
- bb (walks), so (strikeouts)
- pitch_ip (innings pitched), pitch_k (strikeouts), pitch_bb (walks), pitch_er (earned runs)

**Soccer (EPL):**
- epl_goals, epl_assists, epl_shots_on_target
- epl_passes, epl_tackles, epl_saves (for goalkeepers)

### Bet Performance Tracking

The `current_performance` object in each bet matches stat_type to player data:

```javascript
// Mapping examples:
"Player PTS" → player.points
"Player AST" → player.assists
"Player REB" → player.rebounds
"Player STL" → player.steals
"Player BLK" → player.blocks
"Player 3PT" → player.three_pt
"Passing Yards" → player.passing_yards
"Touchdowns" → player.passing_tds || player.receiving_tds
```

## Styling & Design

### Color Palette
- Primary Accent: #00d4ff (cyan)
- Success: #22c155 (green)
- Danger: #ff6b6b (red)
- Background: Linear gradients (dark blue to black)
- Text: rgba(255, 255, 255, 0.8-1.0)

### Responsive Breakpoints
- Desktop: Full grid layouts
- Tablet (1024px): Single column stats
- Mobile (768px): Stacked layouts, horizontal scroll tables

### Animations
- Pulse effect on LIVE badges
- Smooth fade-in on tab changes
- Hover transforms on cards (+translateY, shadow effects)
- Flash effect on score changes

## Performance Optimizations

1. **Concurrent Queries**: Uses `asyncio.gather()` to fetch all data in parallel
2. **Lazy Loading**: Player stats only calculated when tab is viewed
3. **Efficient Lookups**: Team stats aggregated server-side, not client-side
4. **Selective Loading**: Only includes stats relevant to the sport type

## Future Enhancements

1. **Live Updates**: WebSocket integration for real-time score and stat updates
2. **Play-by-Play**: Expandable section showing recent plays
3. **Injury Reports**: Display active injuries for teams/players
4. **Historical Comparison**: Compare this game to season averages
5. **Advanced Analytics**: Expected win probability, efficiency metrics
6. **Sharing**: Share game highlights or bets on social media
7. **Notifications**: Alert on bet status changes or key player milestones
8. **Replay Integration**: Embed video highlights or clips
9. **Heat Maps**: Visual representation of player shooting zones
10. **Player Trending**: Show if a player is hot/cold in the season

## Testing

### API Testing
```bash
curl -X GET "http://localhost:8000/games/{game_id}/detailed"
```

### Frontend Testing
1. Navigate to any live/final game
2. Click "📊 Details" button
3. Verify all tabs load correctly
4. Check player stats display
5. Verify bet performance tracking
6. Test responsive design at different screen sizes

## Known Limitations

1. Data depends on PlayerStats being populated by scraper
2. Team logos must be present in Team model
3. Player headshots must be present in Player model
4. Some sports may have incomplete stat fields
5. No real-time WebSocket updates (yet)

## Database Requirements

This feature relies on:
- `Game` table with team IDs and scores
- `GameUpcoming`, `GameLive`, `GameResult` tables for state
- `PlayerStats` table with detailed player statistics
- `Player` table with headshots and jersey numbers
- `Team` table with logos
- `Bet` table with bet details

Ensure the stats scraper is running to populate `PlayerStats`:
```bash
# In scheduler/tasks.py, the PlayerStatsScraper runs daily
await scheduler.run_scrapers()
```

## Files Modified

1. **Backend:**
   - `backend/routers/games.py` - Added `/games/{game_id}/detailed` endpoint

2. **Frontend:**
   - `frontend/src/pages/GameDetailPage.jsx` - New page component
   - `frontend/src/pages/GameDetailPage.css` - Styling
   - `frontend/src/pages/LiveScoresPage.jsx` - Added Details button
   - `frontend/src/App.jsx` - Added route
   - `frontend/src/styles.css` - Added button styling

## Support

For issues or enhancements, check:
- Browser console for frontend errors
- Server logs for backend errors
- Ensure PlayerStats data exists: `SELECT COUNT(*) FROM player_stats;`
- Verify Game records: `SELECT COUNT(*) FROM games WHERE game_id = ?;`
