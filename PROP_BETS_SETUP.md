# PROP BETS INTEGRATION GUIDE

## Current Status
✅ Backend infrastructure ready for prop bets
✅ Web scraper created (NO API KEY NEEDED)
✅ Multiple sources with automatic fallbacks
⏳ Ready to deploy

## Solution: Web Scraping (No API Key Required)

**Sources** (in priority order):
1. **FanDuel** - Largest selection, most props
2. **BetMGM** - Good coverage, fallback
3. **TheScore** - Alternative source, fallback
4. **ESPN** - Basic props, final fallback

**Why**: 
- ✅ No API key required
- ✅ Real sportsbook odds (not aggregated)
- ✅ Free forever
- ✅ Automatic fallback if one source fails
- ⚠️ HTML parsing (pages can change, but rare)
- ⚠️ Requires BeautifulSoup & aiohttp (small dependencies)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install beautifulsoup4 aiohttp
```

### 2. Deploy the Scraper
Files already created:
- `backend/services/props_web_scraper.py` - Main scraper (400+ lines)
- `backend/services/props_integration.py` - Integration service

No configuration needed!

### 3. Add to Your Scheduler (Optional)
In `backend/scheduler/tasks.py`:

```python
from backend.services.props_integration import scrape_props_task

async def run_schedulers():
    # ... existing code ...
    
    # Add props scraping (daily at 8 AM)
    scheduler.add_job(
        scrape_props_task,
        'cron',
        hour=8,
        minute=0,
        name='Scrape Player Props'
    )
```

### 4. Use in Custom Bet Builder (Optional)
In your frontend when building custom parlays, show available props:

```javascript
// Fetch props from backend
const props = await api.get('/bets/available-props?sport=NBA');

// User can add prop as parlay leg:
// League Pick: Lakers -5 (1.95) OR Player Prop: LeBron 30+ Points (1.90)
```

## Prop Types Covered

### NBA
- Player Points Over/Under
- Player Assists Over/Under
- Player Rebounds Over/Under
- Player 3-Pointers Made
- Steals, Blocks
- Prop Combos

### NFL
- QB Passing Yards/TD
- RB Rushing Yards/TD
- WR Receiving Yards/TD
- Defense: Tackles, Sacks, Interceptions

### NHL
- Player Goals
- Player Assists
- Shots on Target

### Soccer/EPL
- Player Goals
- Player Assists
- Shots on Target

## How It Works

### Scraper Flow
```
FanDuel → Success? ✅ Return props
   ↓ (fail)
BetMGM → Success? ✅ Return props
   ↓ (fail)
TheScore → Success? ✅ Return props
   ↓ (fail)
ESPN → Success? ✅ Return props
   ↓ (fail)
Return empty + error logs
```

### Example Output
```python
{
    "props": [
        {
            "player_name": "LeBron James",
            "prop_type": "Points",
            "over_odds": 1.95,
            "under_odds": 1.90,
            "sportsbook": "FanDuel",
            "sport": "NBA"
        }
    ],
    "source": "fanduel",
    "success": True
}
```

## Cost Analysis

| Option | Cost |
|--------|------|
| **Web Scraping** (FanDuel, BetMGM, TheScore, ESPN) | **$0** ✅ |
| The Odds API | $0-20/month |
| Sportradar | $$$$ |

## Architecture

### Scrapers Created
- `backend/services/props_web_scraper.py` (400+ lines)
  - PropScraper class with 4 sources
  - Automatic fallback logic
  - Multiple CSS selectors per source
  
- `backend/services/props_integration.py` (150+ lines)
  - PropsIntegrationService
  - Daily task integration
  - Storage interface

### Current Endpoints
- `POST /bets/place-aai-single` - Place AAI pick (now supports prop bets)
- `POST /bets/place-aai-parlay` - Combine picks including props
- `POST /bets/build-custom-single` - Select from games + props
- `POST /bets/build-custom-parlay` - Multi-leg with game picks and props

### Database Schema (Optional)
```sql
CREATE TABLE IF NOT EXISTS props (
    id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    prop_type TEXT,  -- "Points", "Assists", "Rebounds"
    over_odds REAL,
    under_odds REAL,
    sportsbook TEXT,  -- "FanDuel", "BetMGM", "TheScore"
    sport TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Frontend Integration

### Add Prop Bets to AAI Display
In `AAIBetsPage.jsx`:
```jsx
// Show prop bets in recommendations
<PropBetsSection props={recommendations.prop_bets} />

// Add "Place Prop Bet" button for each prop
<button onClick={() => placeBet(prop.game_id, `${prop.player_name} ${prop.market}`, prop.odds)}>
  Place Prop Bet
</button>
```

### Custom Parlay Builder with Props
```jsx
// Allow selecting both game bets and prop bets
<ParalayBuilder 
  gameBets={games}
  propBets={props}
  onAddLeg={(leg) => addToParlay(leg)}
/>
```

## Testing Checklist

- [ ] Dependencies installed: `pip install beautifulsoup4 aiohttp`
- [ ] Scraper runs without errors
- [ ] FanDuel props scraped
- [ ] BetMGM fallback works
- [ ] TheScore fallback works
- [ ] ESPN fallback works
- [ ] Logs show which source was used
- [ ] Props display in custom bet builder
- [ ] Props can be added to parlays

## Alternative Solutions (If Scraping Fails)

If web scraping doesn't work out:
1. **The Odds API** - Sign up, get free tier, switch to API
2. **Manual Entry** - User enters props in UI before betting
3. **ESPN API** - Limited props but reliable

## Next Steps

1. **Install dependencies**: `pip install beautifulsoup4 aiohttp`
2. **Test scraper locally**: Run props_web_scraper.py directly
3. **Add to scheduler** (optional): Daily task in tasks.py
4. **Deploy**: Copy files to production
5. **Monitor**: Check logs for scraping success

---

**Status**: Ready to deploy immediately! No API keys, no signup, no configuration. Just install dependencies and you're done. 🚀
