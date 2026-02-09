# External Odds Integration Guide

The AAI recommendations system now supports aggregating probabilities from multiple external model sources. Here's how to integrate them:

## Architecture

The `ExternalOddsAggregator` class manages probability integration:
- **Collects** probabilities from multiple models (as floats: 0.0 to 1.0)
- **Aggregates** them by taking the mean
- **Returns** a dict with each model's individual probability + the mean

## Current Models (Placeholders)

1. **Home Advantage** (always active)
   - Empirical: ~54% win rate for home teams
   - Static value based on sport data

2. **Elo Rating** (placeholder)
   - Method: `_get_elo_probability()`
   - Integration point for external Elo service

3. **Vegas Lines** (placeholder)
   - Method: `_get_vegas_implied_probability()`
   - Integration point for OddsAPI, TheOddsAPI, etc.

4. **Predictive Model** (placeholder)
   - Method: `_get_predictive_model_probability()`
   - Integration point for custom ML model

## Integration Examples

### Adding Custom Elo Ratings

```python
async def _get_elo_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    """Fetch Elo ratings from a custom provider."""
    try:
        # Example: Call external Elo service
        elo_data = await fetch_elo_ratings(game.away_team_name, game.home_team_name)
        
        home_elo = elo_data['home_elo']
        away_elo = elo_data['away_elo']
        
        # Convert Elo difference to probability
        elo_diff = home_elo - away_elo if is_home else away_elo - home_elo
        probability = 1 / (1 + 10 ** (-elo_diff / 400))  # Elo formula
        
        return probability
    except Exception:
        return None
```

### Adding OddsAPI Vegas Lines

```python
async def _get_vegas_implied_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    """Fetch implied probability from Vegas moneyline odds."""
    try:
        odds_data = await fetch_from_oddsapi(
            sport=game.sport.espn_league_code,
            event_id=game.game_id,
            provider='draftkings'
        )
        
        if is_home:
            moneyline = odds_data['home_moneyline']
        else:
            moneyline = odds_data['away_moneyline']
        
        # Use built-in converter
        probability = self.implied_probability_from_moneyline(moneyline)
        return probability
    except Exception:
        return None
```

### Adding Custom ML Model

```python
async def _get_predictive_model_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    """Get prediction from custom ML model endpoint."""
    try:
        features = await prepare_ml_features(game, team_name, is_home)
        
        response = await http_client.post(
            "https://ml-service.internal/predict",
            json=features
        )
        
        probability = response.json()['win_probability']
        return probability
    except Exception:
        return None
```

## Output Format

The `fetch_external_odds()` method returns:

```json
{
  "home_advantage": 0.54,
  "elo": 0.58,
  "vegas": 0.56,
  "predictive_model": 0.61,
  "mean": 0.5725
}
```

This is stored in the recommendation's `external_odds` field.

## Frontend Display

The UI shows:
- **Form Confidence**: Team form-based probability (original AAI logic)
- **Blended Confidence**: Average of Form + External models
- **External Models**: Expandable details showing individual model probabilities

## Updating Confidence Calculation

Currently, the blend is 50/50:
```python
combined_confidence = (form_confidence + external_prob) / 2
```

To adjust weighting, modify in `generate()`:
```python
# Custom weights example: 60% form, 40% external
combined_confidence = (form_confidence * 0.6) + (external_prob * 0.4)
```

## Performance Considerations

- External API calls are made **per-game** in the generate loop
- Consider caching if APIs are rate-limited
- Use timeouts to prevent blocking (example: 2-second per API)
- Fall back gracefully (returns None if API unavailable)

## Testing

Test external model integration:

```python
aggregator = ExternalOddsAggregator()
odds = await aggregator.fetch_external_odds(game, "Team Name", is_home=True)
assert 0.0 <= odds["mean"] <= 1.0
assert "home_advantage" in odds
```
