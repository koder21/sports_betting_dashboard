# External Odds Integration - Quick Reference

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AAI Recommendations                       │
├─────────────────────────────────────────────────────────────┤
│  generate() → for each game:                                │
│   ├─ Form Analysis (Team Win Rate)        → 58% confidence  │
│   ├─ ExternalOddsAggregator.fetch()                         │
│   │  ├─ Home Advantage      → 54%                           │
│   │  ├─ Elo Rating (TODO)   → ? %                           │
│   │  ├─ Vegas Lines (TODO)  → ? %                           │
│   │  └─ ML Model (TODO)     → ? %                           │
│   │  └─ MEAN               → 56.8%                          │
│   ├─ BLEND: (58% + 56.8%) / 2           → 57.4%            │
│   └─ Return: {confidence, combined_confidence, external_odds}│
└─────────────────────────────────────────────────────────────┘
```

## Data Structure

```python
single_recommendation = {
    "pick": "Seattle Seahawks",
    "confidence": 58.0,                    # Form only
    "combined_confidence": 57.4,           # Form + External (50/50)
    "external_odds": {
        "home_advantage": 54.0,
        "elo": 56.0,                       # If integrated
        "vegas": 55.0,                     # If integrated
        "predictive_model": 61.0,          # If integrated
        "mean": 56.8
    }
}
```

## Implementation Checklist

### Phase 1: Basic Integration ✅
- [x] ExternalOddsAggregator class created
- [x] Home advantage model active (54% empirical)
- [x] Placeholder methods for other models
- [x] Mean calculation working
- [x] Frontend displays external odds
- [x] Blending logic (50/50 form + external)

### Phase 2: Vegas Odds Integration
- [ ] Get OddsAPI key from https://the-odds-api.com/
- [ ] Implement `_get_vegas_implied_probability()`
- [ ] Parse moneyline odds and convert to probability
- [ ] Add error handling and timeout
- [ ] Cache results (optional, 60 min TTL)
- [ ] Test with sample games

### Phase 3: Elo Rating Integration
- [ ] Choose Elo source (custom provider, internal model, etc.)
- [ ] Implement `_get_elo_probability()`
- [ ] Calculate: 1 / (1 + 10^(-elo_diff/400))
- [ ] Handle team name mapping
- [ ] Add caching

### Phase 4: ML Model Integration
- [ ] Deploy ML model service (or use existing)
- [ ] Document required features
- [ ] Implement `_get_predictive_model_probability()`
- [ ] Add timeout and error handling
- [ ] Test prediction quality

## File Locations

| What | Where |
|------|-------|
| Core logic | `backend/services/aai/recommendations.py` |
| Frontend display | `frontend/src/pages/AAIBetsPage.jsx` |
| UI styles | `frontend/src/pages/AAIBetsPage.css` |
| Integration guide | `backend/services/aai/EXTERNAL_MODELS_GUIDE.md` |
| Code examples | `backend/services/aai/EXAMPLE_MODELS.py` |
| Test script | `test_external_odds.py` |

## Common Snippets

### Convert Moneyline to Probability
```python
def ml_to_prob(ml: int) -> float:
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)

# Example: -130 = 56.5% probability
prob = ml_to_prob(-130)  # Returns 0.5652
```

### Convert Probability to Moneyline
```python
def prob_to_ml(prob: float) -> int:
    if prob > 0.5:
        return int(-100 * prob / (1 - prob))
    else:
        return int(100 * (1 - prob) / prob)

# Example: 56.5% = -130
ml = prob_to_ml(0.565)  # Returns -130
```

### Simple Elo Calculation
```python
def elo_win_prob(team_elo: float, opponent_elo: float) -> float:
    diff = team_elo - opponent_elo
    return 1 / (1 + 10 ** (-diff / 400))

# Example: 1600 vs 1500 rating
prob = elo_win_prob(1600, 1500)  # Returns ~0.569 (56.9%)
```

## Testing Commands

```bash
# Test aggregation logic
/venv/bin/python test_external_odds.py

# Test backend endpoint
curl http://localhost:8000/aai-bets/recommendations

# Check recommendations in frontend
# Navigate to http://localhost:3000/aai-bets
```

## Adjust Blending Weight

In `generate()` method, find:
```python
combined_confidence = (form_confidence + external_prob) / 2
```

Change to your desired ratio:
```python
# 70% form, 30% external
combined_confidence = form_confidence * 0.7 + external_prob * 0.3

# 40% form, 60% external
combined_confidence = form_confidence * 0.4 + external_prob * 0.6

# 80% external only
combined_confidence = external_prob
```

## Disable External Odds

```python
# Call without external models
recommendations = await recommender.generate(include_external_odds=False)
```

## API Response Format

GET `/aai-bets/recommendations` returns:

```json
{
  "generated_at": "2026-02-10T12:00:00",
  "singles": [
    {
      "game_id": "401772988",
      "pick": "Seattle Seahawks",
      "confidence": 58.0,
      "combined_confidence": 57.4,
      "external_odds": {
        "home_advantage": 54.0,
        "mean": 54.0
      }
    }
  ],
  "parlays": [
    {
      "leg_count": 2,
      "confidence": 33.64,
      "combined_confidence": 32.95,
      "legs": [...]
    }
  ],
  "disclaimer": "..."
}
```

## Environment Variables

Add to `.env`:
```bash
ODDSAPI_KEY=your_key_here
ELO_API_ENDPOINT=https://...
ML_MODEL_ENDPOINT=http://ml-service:5000/predict
```

Then access in code:
```python
import os
api_key = os.getenv("ODDSAPI_KEY")
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| External models not showing | Check if methods return None (failing) |
| Same confidence all models | Placeholder methods returning None, only home_advantage active |
| UI not updating | Clear browser cache, restart backend |
| API errors | Check API key, rate limits, network timeout |
| Slow recommendations | Add caching or timeout to external calls |

## Support

- `EXTERNAL_MODELS_GUIDE.md` - Detailed integration instructions
- `EXAMPLE_MODELS.py` - Ready-to-copy implementations
- `test_external_odds.py` - Working demo script
