# Quick Start: Leaderboards & Weather Features

## Installation

### 1. Set Environment Variables

Add to your `.env` file:

```bash
# OpenWeather API (get free key at openweathermap.org)
OPENWEATHER_API_KEY=your_key_here
```

### 2. No Database Changes Needed

✅ Your existing database already has:
- `weather` columns in `games_upcoming` and `games_results`
- `injuries` table for injury tracking
- `bets.reason` field to track forecasters
- All necessary tables for leaderboard tracking

### 3. Backend is Ready

All new endpoints are automatically registered when backend starts:

```bash
cd backend
python -m uvicorn main:app --reload
```

## Using Forecaster Leaderboards

### Track Your Forecasters

When placing bets, include a `reason` field:

```python
# This identifies which model/forecaster made this pick
bet = {
    "raw_text": "NFL Game 123: Home Team -110",
    "stake": 100.0,
    "odds": 1.91,
    "reason": "aai_model"  # ← This becomes the forecaster name
}
```

### View Leaderboards

```bash
# All forecasters, last 90 days
curl "http://localhost:8000/leaderboards/forecasters/leaderboard"

# Top 10, NFL only
curl "http://localhost:8000/leaderboards/forecasters/leaderboard?sport=NFL&limit=10"

# Last 30 days
curl "http://localhost:8000/leaderboards/forecasters/leaderboard?days=30"
```

### Check Specific Forecaster

```bash
# Full stats
curl "http://localhost:8000/leaderboards/forecasters/aai_model/stats"

# By sport breakdown
curl "http://localhost:8000/leaderboards/forecasters/aai_model/by-sport"

# Current win/loss streak
curl "http://localhost:8000/leaderboards/forecasters/aai_model/streak"

# Best contrarian picks (ROI > 10%)
curl "http://localhost:8000/leaderboards/forecasters/aai_model/contrarian"
```

## Using Weather Integration

### Get Weather for a Game

```bash
# Just weather data
curl "http://localhost:8000/leaderboards/weather/MetLife%20Stadium?city=East%20Rutherford"

# Weather + NFL impact analysis
curl "http://localhost:8000/leaderboards/weather/MetLife%20Stadium?city=East%20Rutherford&sport=NFL"

# Baseball weather (wind impact on overs)
curl "http://localhost:8000/leaderboards/weather/Fenway%20Park?city=Boston&sport=MLB"
```

### Interpreting Weather Impact

**NFL Example:**
```json
{
  "is_harsh_conditions": true,
  "overs_adjustment": 0.92,          // 8% adjustment down from overs total
  "passing_game_affected": true,      // Wind > 15mph
  "kicking_affected": false,          // Wind not extreme
  "recommendation": "Harsh wind: favor running game, under-heavy lineups"
}
```

**Baseball Example:**
```json
{
  "overs_adjustment": 1.08,           // 8% adjustment UP (wind blowing out)
  "wind_helps_hitters": true,         // Wind direction = "Out"
  "recommendation": "Wind blowing out: favor overs"
}
```

## Frontend Integration Examples

### Display Forecaster Leaderboards

```javascript
// Fetch leaderboard
const response = await fetch('/leaderboards/forecasters/leaderboard?days=90&limit=10');
const data = await response.json();

// Render table
data.leaderboard.forEach(forecaster => {
  console.log(`${forecaster.forecaster}: ${forecaster.roi}% ROI (${forecaster.win_rate}% wins)`);
});
```

### Show Weather on Game Card

```javascript
// Get weather for game venue
const weather = await fetch(
  `/leaderboards/weather/${game.venue}?city=${game.city}&sport=${game.sport}`
);
const data = await weather.json();

// Display on UI
if (data.weather) {
  const temp = data.weather.temp;
  const wind = data.weather.wind_speed;
  const harsh = data.weather.is_harsh ? '⚠️ Harsh' : '✓ Normal';
  console.log(`${temp}°F, Wind: ${wind}mph ${harsh}`);
}

// Show impact if available
if (data.impact?.overs_adjustment) {
  const adjustment = ((data.impact.overs_adjustment - 1) * 100).toFixed(1);
  console.log(`Overs adjustment: ${adjustment}%`);
}
```

### Leaderboards Dashboard Component

```javascript
// React component example
function ForecasterLeaderboard() {
  const [leaderboard, setLeaderboard] = useState([]);
  
  useEffect(() => {
    fetch('/leaderboards/forecasters/leaderboard?limit=20')
      .then(r => r.json())
      .then(data => setLeaderboard(data.leaderboard));
  }, []);
  
  return (
    <table>
      <thead>
        <tr>
          <th>Forecaster</th>
          <th>ROI</th>
          <th>Win Rate</th>
          <th>Profit</th>
          <th>Bets</th>
        </tr>
      </thead>
      <tbody>
        {leaderboard.map(f => (
          <tr key={f.forecaster}>
            <td>{f.forecaster}</td>
            <td className={f.roi > 0 ? 'profit' : 'loss'}>{f.roi}%</td>
            <td>{f.win_rate}%</td>
            <td>${f.total_profit.toFixed(2)}</td>
            <td>{f.total_bets}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

## Performance Notes

### Leaderboards

- Queries optimized with aggregations and grouping
- Caches don't need to be manually refreshed
- For 1000+ bets, consider limiting time window to 30-60 days

### Weather

- Results cached by venue/city to minimize API calls
- Free tier limit: 60 calls/minute
- Typical game: 1-2 API calls (venue lookup + data fetch)

## Metrics Explained

### ROI (Return on Investment)
- Calculation: `(Total Profit / Total Wagered) × 100`
- Example: Wagered $1000, Profit $150 = 15% ROI
- Interpretation: How much profit per dollar wagered

### Win Rate
- Calculation: `(Wins / Total Bets) × 100`
- Example: 10 wins out of 20 bets = 50% win rate
- Interpretation: How often picks win

### Consensus Strength
- Scale: 0-100 (higher = more model agreement)
- 80+: Very confident consensus
- 60-80: Good consensus
- <60: Mixed signals from models

## Troubleshooting

### Leaderboard queries slow?
Check if forecaster has many bets. Try:
- Reduce time window: `?days=30`
- Limit results: `?limit=10`

### Weather API returning null?
Check:
- API key is valid in `.env`
- Venue name matches location (e.g., "Lambeau Field", "Green Bay")
- API has remaining quota

### No leaderboard data?
Ensure:
- Bets have been graded (`status = "graded"`)
- Bets have a `reason` field
- Bets are within time window (default 90 days)

## Next Steps

1. **Update your bet placement code** to include `reason` field
2. **Test weather API** with a venue near you
3. **Build forecaster dashboard** showing top performers
4. **Add weather widgets** to game cards
5. **Monitor streaks** and adjust model weights based on recent performance

## Full Documentation

See [LEADERBOARDS_WEATHER_README.md](LEADERBOARDS_WEATHER_README.md) for complete API reference.
