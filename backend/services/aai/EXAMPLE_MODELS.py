# Example External Model Implementations

This file provides ready-to-use examples for integrating specific external probability sources.

## 1. Custom Elo Ratings

```python
# In backend/services/aai/external_models/elo_model.py

import aiohttp
from typing import Optional, Dict

class EloRatingsClient:
    """Fetch team Elo ratings from a custom provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://YOUR_ELO_SOURCE/elo.csv"
    
    async def get_team_elo(self, team_name: str, sport: str) -> Optional[float]:
        """Get current Elo rating for team."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url) as resp:
                    if resp.status != 200:
                        return None
                    
                    csv_data = await resp.text()
                    # Parse CSV and find team
                    for line in csv_data.split('\n'):
                        if team_name.lower() in line.lower():
                            parts = line.split(',')
                            return float(parts[-1])  # Last column is Elo
            return None
        except Exception:
            return None
    
    def elo_to_probability(self, elo_diff: float) -> float:
        """Convert Elo difference to win probability."""
        # Standard Elo formula
        return 1 / (1 + 10 ** (-elo_diff / 400))
```

Usage:
```python
async def _get_elo_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    client = EloRatingsClient()
    
    home_elo = await client.get_team_elo(game.home_team_name, game.sport)
    away_elo = await client.get_team_elo(game.away_team_name, game.sport)
    
    if not home_elo or not away_elo:
        return None
    
    elo_diff = (home_elo - away_elo) if is_home else (away_elo - home_elo)
    return client.elo_to_probability(elo_diff)
```

## 2. OddsAPI Vegas Lines

```python
# In backend/services/aai/external_models/vegas_model.py

import aiohttp
from typing import Optional

class VegasOddsClient:
    """Fetch Vegas odds from OddsAPI."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    async def get_game_odds(self, sport_key: str, game_id: str) -> Optional[Dict]:
        """Fetch odds for specific game."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sports/{sport_key}/odds"
                params = {
                    "apiKey": self.api_key,
                    "regions": "us",
                    "markets": "h2h",
                    "oddsFormat": "american",
                }
                
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    # Find matching game
                    for game in data.get("games", []):
                        if game["id"] == game_id or game.get("external_id") == game_id:
                            return game
            return None
        except Exception:
            return None
    
    def implied_probability_from_moneyline(self, moneyline: int) -> float:
        """Convert American moneyline to implied probability."""
        if moneyline > 0:
            return 100 / (moneyline + 100)
        else:
            return abs(moneyline) / (abs(moneyline) + 100)
```

Usage:
```python
async def _get_vegas_implied_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    client = VegasOddsClient(api_key=os.getenv("ODDSAPI_KEY"))
    
    odds_data = await client.get_game_odds(
        sport_key=game.sport.espn_league_code,
        game_id=game.game_id
    )
    
    if not odds_data:
        return None
    
    # Find bookmakers with highest limits (DraftKings, FanDuel, etc.)
    for bookmaker in odds_data.get("bookmakers", []):
        if bookmaker["key"] in ["draftkings", "fanduel"]:
            for outcome in bookmaker["markets"][0]["outcomes"]:
                if outcome["name"].lower() == team_name.lower():
                    ml = outcome["price"]
                    return client.implied_probability_from_moneyline(int(ml))
    
    return None
```

## 3. Custom ML Model (Local Service)

```python
# In backend/services/aai/external_models/ml_model.py

import aiohttp
from typing import Optional, Dict, Any

class MLModelClient:
    """Query custom ML model for predictions."""
    
    def __init__(self, endpoint: str, timeout: int = 2):
        self.endpoint = endpoint
        self.timeout = timeout
    
    async def predict(self, features: Dict[str, Any]) -> Optional[float]:
        """Get win probability from ML model."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json=features,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    return data.get("win_probability")
        except Exception:
            return None
```

Usage:
```python
async def _get_predictive_model_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    # Prepare features
    features = {
        "home_team": game.home_team_name,
        "away_team": game.away_team_name,
        "sport": game.sport.name,
        "is_home": is_home,
        "is_neutral": game.neutral_site or False,
        "start_time": game.start_time.isoformat() if game.start_time else None,
    }
    
    client = MLModelClient(
        endpoint=os.getenv("ML_MODEL_ENDPOINT"),
        timeout=2
    )
    
    return await client.predict(features)
```

## 4. Example Feature Preparation

```python
# Helper for ML model features

from datetime import datetime

async def prepare_ml_features(
    game: Game,
    session: AsyncSession,
    team_name: str,
    is_home: bool,
) -> Dict[str, Any]:
    """Prepare rich feature set for ML prediction."""
    
    # Get team form
    home_form = await get_team_form(session, game.home_team_name)
    away_form = await get_team_form(session, game.away_team_name)
    
    features = {
        "home_team": game.home_team_name,
        "away_team": game.away_team_name,
        "sport": game.sport.name,
        "is_home": is_home,
        "target_team": team_name,
        
        # Form features
        "home_recent_wins": home_form.wins if home_form else 0,
        "away_recent_wins": away_form.wins if away_form else 0,
        "home_wr": home_form.win_rate if home_form else 0.5,
        "away_wr": away_form.win_rate if away_form else 0.5,
        
        # Context
        "neutral_site": game.neutral_site or False,
        "day_of_week": game.start_time.weekday() if game.start_time else 0,
        "hour": game.start_time.hour if game.start_time else 12,
    }
    
    return features
```

## 5. Caching Strategy (Optional)

```python
# In backend/services/aai/external_models/cache.py

from datetime import datetime, timedelta
from typing import Dict, Optional, Any

class OddsCache:
    """Simple in-memory cache for external model results."""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if datetime.now() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Store value with timestamp."""
        self.cache[key] = (value, datetime.now())
    
    def clear_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now()
        expired_keys = [
            k for k, (_, ts) in self.cache.items()
            if now - ts > self.ttl
        ]
        for k in expired_keys:
            del self.cache[k]
```

## Integration Checklist

- [ ] Set API keys in `.env` file
- [ ] Add client classes to `backend/services/aai/external_models/`
- [ ] Implement `_get_*_probability()` methods in `ExternalOddsAggregator`
- [ ] Test with sample data
- [ ] Add error handling and timeouts
- [ ] Monitor API rate limits
- [ ] Document API response schema
- [ ] Add unit tests for each model
