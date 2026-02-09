# Analysis & Implementation Plan

## Current State Analysis

### ✅ What's Already Working

1. **Weather IS scraped** 
   - Location: `backend/services/scraper_stats.py` line 455-458
   - Scraped from ESPN's game data during boxscore processing
   - Stored in: `games_results.weather` (completed games)
   - Format: Display value from ESPN (e.g., "Clear, 72°F, Wind 5mph")

2. **Injuries ARE scraped**
   - Location: `backend/services/scraping/common_team_league.py` line 247
   - Scraped from ESPN's team injury reports
   - Stored in: `injuries` table with player_id, team_id, description, status
   - Used by: InjuryRepository

3. **Database schema has both**
   - `games_upcoming.weather` - TEXT
   - `games_results.weather` - TEXT
   - `injuries` table - Full injury tracking

### ❌ What's NOT Implemented

1. **Weather is NOT used in AAI recommendations**
   - AAI only looks at: team form (win/loss), external models (Vegas, Elo, ML, Kelly)
   - Weather data sits unused in database

2. **Injuries are NOT used in AAI recommendations**
   - Injuries are scraped but not factored into confidence scores
   - No "key player out" adjustments

3. **No "fresh info" verification before bet placement**
   - AAI generates recommendations from cached database data
   - No real-time checks before actual money placement

4. **Weather from ESPN only (post-game)**
   - ESPN weather is only available AFTER games complete
   - No forecasted weather for upcoming games

---

## Implementation Plan

### Phase 1: Add Weather & Injury Checks to AAI ✅ (New Feature)

**What**: Before generating recommendations, check:
- Harsh weather conditions (wind, rain, temp)
- Key injuries for each team
- Adjust confidence scores accordingly

**Files to modify**:
- `backend/services/aai/recommendations.py` - Add injury/weather checks

### Phase 2: "Fresh Info" Pre-Bet Verification ✅ (New Feature)

**What**: New endpoint `/aai-bets/verify-before-bet/{game_id}` that:
- Fetches FRESH data for a specific game
- Re-scrapes latest injuries from ESPN
- Gets current weather forecast
- Re-checks odds from ESPN
- Returns comprehensive "bet readiness" report

**Files to create**:
- `backend/services/aai/pre_bet_verifier.py` - Fresh data checker

### Phase 3: Switch to Open-Meteo ✅ (Your Request)

**What**: Replace OpenWeather with Open-Meteo (free, no API key needed)
- Better forecasting
- Completely free (no limits)
- More detailed data

**Files to modify**:
- `backend/services/weather.py` - Switch API from OpenWeather to Open-Meteo

---

## Why Open-Meteo?

✅ **Advantages over OpenWeather**:
- Completely free, no API key needed
- No rate limits
- Better forecast accuracy (7-day)
- Historical weather data included
- Open source, community-driven

❌ **OpenWeather drawbacks**:
- Requires API key
- Free tier: only 60 calls/minute
- Limited forecast data

**Decision**: Switch to Open-Meteo

---

## Implementation Details

### 1. Weather Integration in AAI

```python
# In recommendations.py _team_form():
async def _check_weather_impact(self, game_id: str) -> Optional[WeatherImpact]:
    # Get forecasted weather for game venue
    # Adjust confidence if harsh conditions detected
    # Return impact assessment
```

### 2. Injury Integration in AAI

```python
# In recommendations.py generate():
async def _check_key_injuries(self, team_id: str) -> InjuryImpact:
    # Query injuries table for team
    # Identify "key player" injuries (starters, high usage)
    # Reduce confidence if key players out
```

### 3. Fresh Info Verifier (New Service)

```python
class PreBetVerifier:
    async def verify_game(self, game_id: str) -> Dict[str, Any]:
        # 1. Re-scrape injuries (fresh from ESPN)
        # 2. Get weather forecast (Open-Meteo)
        # 3. Re-check odds (ESPN latest)
        # 4. Verify game hasn't been postponed
        # 5. Check for lineup changes
        # 6. Return comprehensive report
```

### 4. Open-Meteo Weather Service

```python
# New weather.py using Open-Meteo API
class OpenMeteoWeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    async def get_forecast(self, lat: float, lon: float) -> WeatherData:
        # No API key needed!
        # Returns 7-day forecast with hourly data
```

---

## Next Steps

I'll implement all three features now:
1. ✅ Switch weather service to Open-Meteo
2. ✅ Add weather/injury checks to AAI recommendations
3. ✅ Create fresh info pre-bet verifier endpoint
