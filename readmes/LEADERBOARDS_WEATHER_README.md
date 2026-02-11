# Forecaster Leaderboards & Weather Integration

This document covers the two new major features added to the sports betting dashboard: **Forecaster Performance Leaderboards** and **Weather Impact Analysis**.

## 1. Forecaster Leaderboards

### Overview

Track and rank the performance of all your forecasts/betting models using a comprehensive leaderboard system. Every bet you place is associated with a forecaster/model name (via the `reason` field), and the system automatically calculates performance metrics.

### Key Metrics

- **ROI (Return on Investment)**: Percentage profit/loss relative to total wagered
- **Win Rate**: Percentage of bets that won
- **Accuracy**: Hit rate across different sports
- **Streaks**: Current win/loss streak and recent performance
- **Contrarian Picks**: Highest-ROI bets for each forecaster

### API Endpoints

#### GET `/leaderboards/forecasters/leaderboard`

Get full forecaster leaderboard ranked by ROI.

**Query Parameters:**
- `sport` (optional): Filter by sport (e.g., "NFL", "NBA")
- `days` (int): Days of history to include (default: 90)
- `limit` (int): Max results to return (default: 50)

**Example:**
```bash
curl "http://localhost:8000/leaderboards/forecasters/leaderboard?days=90&limit=20"
```

**Response:**
```json
{
  "status": "ok",
  "period": "Last 90 days",
  "count": 5,
  "leaderboard": [
    {
      "forecaster": "aai_model",
      "total_bets": 45,
      "total_wagered": 2250,
      "total_profit": 337.50,
      "wins": 29,
      "roi": 15.0,
      "win_rate": 64.44,
      "avg_odds": 50.0
    },
    {
      "forecaster": "form_analysis",
      "total_bets": 38,
      "total_wagered": 1900,
      "total_profit": 142.50,
      "wins": 25,
      "roi": 7.5,
      "win_rate": 65.79,
      "avg_odds": 50.0
    }
  ]
}
```

#### GET `/leaderboards/forecasters/{forecaster}/stats`

Get detailed stats for a specific forecaster.

**Query Parameters:**
- `days` (int): Days of history (default: 90)

**Example:**
```bash
curl "http://localhost:8000/leaderboards/forecasters/aai_model/stats"
```

**Response:**
```json
{
  "status": "ok",
  "stats": {
    "forecaster": "aai_model",
    "period_days": 90,
    "total_bets": 45,
    "total_wagered": 2250.0,
    "total_profit": 337.50,
    "roi": 15.0,
    "wins": 29,
    "losses": 16,
    "win_rate": 64.44,
    "avg_profit_per_bet": 7.5,
    "biggest_win": 125.0,
    "biggest_loss": -85.0
  }
}
```

#### GET `/leaderboards/forecasters/{forecaster}/by-sport`

Get accuracy breakdown by sport for a forecaster.

**Example:**
```bash
curl "http://localhost:8000/leaderboards/forecasters/aai_model/by-sport"
```

**Response:**
```json
{
  "status": "ok",
  "forecaster": "aai_model",
  "breakdown": [
    {
      "sport": "NFL",
      "bets": 25,
      "roi": 18.5,
      "win_rate": 68.0,
      "profit": 115.50
    },
    {
      "sport": "NBA",
      "bets": 20,
      "roi": 10.0,
      "win_rate": 60.0,
      "profit": 40.0
    }
  ]
}
```

#### GET `/leaderboards/forecasters/{forecaster}/streak`

Get current win/loss streak and recent performance.

**Response:**
```json
{
  "status": "ok",
  "forecaster": "aai_model",
  "streak": {
    "current_streak": 4,
    "streak_type": "wins",
    "recent_bets": [
      {
        "profit": 50.0,
        "graded_at": "2026-02-08 15:30:00"
      }
    ]
  }
}
```

#### GET `/leaderboards/forecasters/{forecaster}/contrarian`

Get highest-ROI picks (contrarian/valuable bets).

**Query Parameters:**
- `days` (int): Days to analyze (default: 30)
- `min_roi` (float): Minimum ROI threshold (default: 10.0)

**Response:**
```json
{
  "status": "ok",
  "forecaster": "aai_model",
  "min_roi": 10.0,
  "picks": [
    {
      "bet": "Game 123: Home Team ML",
      "stake": 100.0,
      "profit": 45.0,
      "roi": 45.0,
      "odds": 1.45,
      "placed_at": "2026-02-01 10:00:00",
      "graded_at": "2026-02-02 23:15:00"
    }
  ]
}
```

### How It Works

1. **Track forecasters**: Every bet should include a `reason` field that identifies the source/model:
   ```json
   {
     "raw_text": "Game 123: Home Team -110",
     "stake": 100,
     "odds": 1.91,
     "reason": "aai_model"  // This becomes the forecaster name
   }
   ```

2. **Automatic calculation**: System tracks:
   - Total bets placed
   - Total wagered
   - Wins/losses
   - Profit/loss
   - ROI and win rate

3. **Historical analysis**: 
   - 90-day default window (configurable)
   - Sport-specific breakdowns
   - Win streaks and contrarian picks

### Use Cases

- **Compare Models**: See which forecasting model performs best
- **Season Analysis**: Track performance across different sports and seasons
- **Find Edges**: Identify which forecasters have proven edges in specific sports
- **Risk Management**: Monitor underperforming forecasters and adjust accordingly

---

## 2. Weather Integration

### Overview

Real-time weather data for game venues with impact analysis on sports betting. Integrates OpenWeather API to provide:
- Current and forecast weather conditions
- Sport-specific impact analysis
- Recommendations for over/under adjustments
- Wind, temperature, and precipitation impacts

### Setup

Add OpenWeather API key to your `.env`:
```bash
OPENWEATHER_API_KEY=your_api_key_here
```

Get a free API key at [openweathermap.org](https://openweathermap.org/api)

### API Endpoints

#### GET `/leaderboards/weather/{venue}`

Get weather data for a venue.

**Query Parameters:**
- `city` (optional): City name for more accurate location
- `sport` (optional): Sport for impact analysis (e.g., "NFL", "NBA", "MLB")

**Example:**
```bash
# Weather for MetLife Stadium
curl "http://localhost:8000/leaderboards/weather/MetLife%20Stadium?city=East%20Rutherford&sport=NFL"
```

**Response (with sport):**
```json
{
  "status": "ok",
  "venue": "MetLife Stadium",
  "city": "East Rutherford",
  "sport": "NFL",
  "weather": {
    "temp": 28,
    "wind_speed": 18,
    "wind_direction": "NW",
    "humidity": 65,
    "precipitation": 0,
    "condition": "Clear",
    "feels_like": 22,
    "is_harsh": true
  },
  "impact": {
    "is_harsh_conditions": true,
    "overs_adjustment": 0.95,
    "passing_game_affected": true,
    "kicking_affected": false,
    "recommendation": "Harsh wind: favor running game, under-heavy lineups"
  }
}
```

**Response (without sport):**
```json
{
  "status": "ok",
  "venue": "MetLife Stadium",
  "city": "East Rutherford",
  "weather": {
    "temp": 28,
    "wind_speed": 18,
    "wind_direction": "NW",
    "humidity": 65,
    "precipitation": 0,
    "condition": "Clear",
    "feels_like": 22,
    "is_harsh": true
  }
}
```

### Weather Data Fields

- **temp**: Temperature in Fahrenheit
- **wind_speed**: Wind speed in mph
- **wind_direction**: Cardinal direction (N, NE, E, SE, S, SW, W, NW)
- **humidity**: Relative humidity (0-100%)
- **precipitation**: Rainfall in mm (last hour)
- **condition**: Weather description (Clear, Cloudy, Rainy, etc.)
- **feels_like**: "Feels like" temperature in Fahrenheit
- **is_harsh**: Boolean indicating harsh weather conditions

### Impact Analysis by Sport

#### Football (NFL/NCAAF)

Weather factors affect:
- **Wind speed > 15 mph**: 
  - Reduces passing game accuracy
  - Affects kicking distance
  - Favors running game
  - Adjustment: -5% to overs

- **Wind speed > 25 mph**: Harsh conditions
  - Very inaccurate passing
  - Possible kicking issues
  - Adjustment: -10% to overs

- **Precipitation > 0.5 mm**: Heavy rain
  - Reduced offensive output
  - Defensive advantage
  - Adjustment: -8% to overs

- **Temperature < 20°F**: Extreme cold
  - Slower offensive pace
  - Affects ball handling
  - Adjustment: -4% to overs

#### Baseball (MLB)

Weather factors:
- **Hot days (>85°F)**: Ball carries further → favor overs
- **Wind out**: Ball travels further → favor overs
- **Wind in**: Ball doesn't carry → favor unders
- **Precipitation**: Reduced offense → favor unders

#### Basketball (NBA/NCAAB)

- Indoor sport, minimal direct weather impact
- Wind/precipitation don't affect play

### Usage Examples

**Check NFL game weather:**
```python
import aiohttp
from backend.services.weather import WeatherService

service = WeatherService()
impact = await service.get_weather_impact_on_game(
    venue="Lambeau Field",
    sport="NFL",
    city="Green Bay"
)
print(f"Overs adjustment: {impact['impact']['overs_adjustment']}")
# Output: 0.92 (8% adjustment down)
```

**Harsh weather detection:**
```python
if impact['weather']['is_harsh']:
    print("Harsh conditions - avoid high-scoring props")
```

### Database Integration

The schema already includes weather columns in:
- `games_upcoming.weather` (TEXT)
- `games_results.weather` (TEXT)

You can populate these with the weather data from this service during game processing.

---

## 3. Consensus Scoring (Enhanced Model Aggregation)

### Overview

Analyzes agreement between external prediction models to generate confidence scores and detect contrarian value.

### How It Works

The AAI recommendations engine now provides:

1. **Consensus Strength** (0-100): How much models agree
   - 100 = all models predict same outcome
   - 0 = models completely disagree

2. **Model Agreement %**: Percentage of models predicting the favorite

3. **Edge Magnitude**: How strong the consensus pick is (distance from 50%)

4. **Contrarian Value Detection**: When models diverge from market odds

### API Integration

The consensus scoring is used internally in `/aai-bets/recommendations`:

```python
# In recommendations.py
probabilities = await aggregator.fetch_external_odds(
    game=game,
    team_name=team,
    is_home=True
)

# Get consensus analysis
consensus = aggregator.get_consensus_strength(probabilities)
print(consensus)
# {
#   "consensus_strength": 78.5,
#   "consensus_probability": 0.623,
#   "model_agreement": 85.0,
#   "is_confident": True,
#   "models_count": 5,
#   "std_deviation": 0.042,
#   "consensus_pick": "home_favorite",
#   "edge_magnitude": 0.123
# }

# Detect contrarian value
value = aggregator.detect_contrarian_value(
    consensus_prob=0.623,
    market_prob=0.55,
    confidence=78.5
)
print(value)
# {
#   "has_contrarian_value": True,
#   "value_amount": 0.065,
#   "pick_type": "undervalued",
#   "confidence_adjusted": True
# }
```

### Confidence Interpretation

- **80-100**: Very high confidence - multiple models agree strongly
- **60-80**: Good confidence - models mostly agree
- **40-60**: Moderate uncertainty - mixed signals
- **0-40**: Low confidence - models disagree significantly

---

## Integration Examples

### Complete Betting Workflow with All Features

```python
from backend.services.weather import WeatherService
from backend.services.aai.recommendations import AAIBetRecommender
from backend.repositories.forecaster_leaderboard import ForecasterLeaderboardRepo

# 1. Get weather conditions
weather_service = WeatherService()
weather = await weather_service.get_weather_impact_on_game(
    venue="MetLife Stadium",
    sport="NFL"
)

# 2. Get model recommendations with consensus
recommender = AAIBetRecommender(session)
recs = await recommender.get_recommendations(
    sport="NFL",
    game_date="2026-02-10"
)

# 3. Filter by weather + consensus
high_confidence_picks = [
    rec for rec in recs
    if rec['consensus_strength'] > 70  # High model agreement
    and not weather['impact']['is_harsh_conditions']  # Favorable weather
]

# 4. Track performance with leaderboards
leaderboard_repo = ForecasterLeaderboardRepo(session)
stats = await leaderboard_repo.get_forecaster_stats("aai_model")
print(f"Current ROI: {stats['roi']}%")
```

### Dashboard Display Example

Frontend can now show:
1. **Main leaderboard**: Top forecasters by ROI
2. **Weather widget**: Current conditions + impact on today's games
3. **Model consensus**: Bar chart showing model agreement
4. **Streaks**: Win/loss streaks for each forecaster
5. **Contrarian picks**: High-ROI bets by forecaster

---

## Configuration

### Weather Service Cache

The weather service caches results by venue/city to avoid excessive API calls.

To clear cache (if needed):
```python
service = WeatherService()
service.cache.clear()
```

### API Rate Limiting

OpenWeather free tier: 60 calls/minute per IP

The service caches results to stay within limits.

### Leaderboard Query Performance

For large bet histories (1000+ bets), queries use efficient grouping and aggregation.
Consider adding indexes if experiencing slow responses:

```sql
CREATE INDEX idx_bets_reason ON bets(reason);
CREATE INDEX idx_bets_sport_graded ON bets(sport_id, status, graded_at);
```

---

## Troubleshooting

### Weather API not working

```
Error: "Weather API error: ..."
```

Check:
1. `OPENWEATHER_API_KEY` is set in `.env`
2. API key is valid and has quota remaining
3. Venue name is spelled correctly

### Leaderboard shows no results

Check:
1. Bets have been graded (`status = "graded"`)
2. Bets have a `reason` field (forecaster name)
3. Time window includes graded bets (default 90 days)

### Slow consensus queries

If recommendations are slow:
1. Limit number of games queried
2. Cache external model results
3. Consider using read replicas for analytics queries

---

## Future Enhancements

- **Historical weather database**: Track weather patterns over seasons
- **Player-specific weather impact**: How individual players perform in different weather
- **Injury weather correlation**: How injuries are more common in certain weather
- **Market sentiment**: Track how odds move based on weather changes
- **Mobile notifications**: Alert users to harsh weather changes before game time
