# External Model Odds Integration - Implementation Summary

## Overview

You now have a complete **external model probability aggregation system** integrated into your AAI Bets recommendations. The system:

✅ **Collects** probabilities from multiple external model sources  
✅ **Calculates** the mean across all available models  
✅ **Blends** external models with your form-based confidence (50/50 weight)  
✅ **Displays** both individual and blended confidence in the UI  
✅ **Provides** detailed breakdowns of all models used

## Architecture Changes

### Backend: `backend/services/aai/recommendations.py`

**New Class: `ExternalOddsAggregator`**
- `fetch_external_odds(game, team_name, is_home)` → fetches all models and returns mean
- `implied_probability_from_moneyline(ml)` → converts Vegas odds to probability
- `moneyline_from_probability(prob)` → converts probability to odds
- Placeholder methods for integrating:
  - Elo ratings
  - Vegas implied odds
  - Custom ML models

**Modified: `AAIBetRecommender.generate()`**
- New parameter: `include_external_odds: bool = True`
- Calls `fetch_external_odds()` for each single bet
- Returns two confidence scores:
  - `confidence`: Form-based only (original logic)
  - `combined_confidence`: 50% form + 50% external mean
- Includes `external_odds` dict with all model probabilities

**Modified: `_build_parlays()`**
- Uses `combined_confidence` for parlay calculations
- Includes both confidence scores in output

### Frontend: `frontend/src/pages/AAIBetsPage.jsx`

**New Features:**
- Displays "Form" confidence (team form analysis)
- Displays "Blended" confidence (form + external models)
- Expandable "External Models" section showing:
  - Each model's individual probability
  - Mean probability calculation

**New Component: `renderExternalOdds()`**
- Shows breakdown of all models in collapsible details
- Formatted as percentage with model names

### Frontend: `frontend/src/pages/AAIBetsPage.css`

**New Styles:**
- `.aai-confidence-column`: Vertical layout for dual confidence display
- `.aai-confidence-label`: Label for confidence type (Form/Blended)
- `.aai-confidence-combined`: Blue styling for blended confidence
- `.aai-external-odds`: Collapsible odds breakdown section
- `.odds-breakdown`: Grid layout for model list
- `.odds-item`: Individual model row styling

## Current Data Flow

```
AAIBetRecommender.generate()
├─ For each upcoming game:
│  ├─ Get team form (win rate)
│  ├─ Calculate form-based confidence
│  ├─ Call odds_aggregator.fetch_external_odds()
│  │  ├─ Home advantage (always active): 54% for home
│  │  ├─ Elo probability (placeholder): None → skipped
│  │  ├─ Vegas implied (placeholder): None → skipped
│  │  ├─ Predictive model (placeholder): None → skipped
│  │  └─ Calculate mean of all available models
│  ├─ Blend: combined = (form + external_mean) / 2
│  └─ Return pick with both confidence scores + odds dict
└─ Sort by combined_confidence
```

## Output Example

A single bet recommendation now includes:

```json
{
  "game_id": "401772988",
  "pick": "Seattle Seahawks",
  "home": "Seattle Seahawks",
  "away": "New England Patriots",
  "start_time": "2026-02-10T15:30:00",
  "confidence": 58.0,
  "combined_confidence": 57.4,
  "reason": "Recent form: Seattle 4/5 (80%) vs New England 2/5 (40%)",
  "external_odds": {
    "home_advantage": 54.0,
    "predictive_model": 61.0,
    "mean": 56.8
  },
  "data_points": {
    "home_games": 5,
    "away_games": 5
  }
}
```

## Integration Guide: Adding External Models

### Option 1: Custom Elo Ratings

```python
async def _get_elo_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    # Call custom Elo API
    # Calculate: 1 / (1 + 10^(-elo_diff/400))
    # Return probability or None if unavailable
    return None  # Replace with actual implementation
```

### Option 2: Vegas Line Implied Odds (OddsAPI)

```python
async def _get_vegas_implied_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    # Call OddsAPI or TheOddsAPI
    # Extract moneyline for DraftKings/FanDuel
    # Convert to probability: 100/(ML+100) or |ML|/(|ML|+100)
    # Return probability or None
    return None  # Replace with actual implementation
```

### Option 3: Custom ML Model

```python
async def _get_predictive_model_probability(self, game: Game, team_name: str, is_home: bool) -> Optional[float]:
    # Call your ML model service
    # Send game/team features as JSON
    # Extract win_probability from response
    return None  # Replace with actual implementation
```

See `EXTERNAL_MODELS_GUIDE.md` for detailed examples.

## Testing

Run the test script to see the aggregation logic:

```bash
/venv/bin/python test_external_odds.py
```

Output shows:
- Individual model probabilities
- Mean calculation
- Blended confidence (form + external)
- Moneyline odds equivalents
- JSON payload for frontend

## Customization

### Adjust Blending Weight

Change the confidence blend ratio in `generate()`:

```python
# Currently: 50% form, 50% external
combined_confidence = (form_confidence + external_prob) / 2

# Option: 60% form, 40% external (trust form more)
combined_confidence = form_confidence * 0.6 + external_prob * 0.4

# Option: 40% form, 60% external (trust models more)
combined_confidence = form_confidence * 0.4 + external_prob * 0.6
```

### Enable/Disable External Odds

```python
# Skip external models entirely
recommendations = await recommender.generate(include_external_odds=False)

# Get only form-based confidence
```

### Add More Models

Simply add new methods and they'll be included automatically:

```python
# In ExternalOddsAggregator.fetch_external_odds()
advanced_stats_prob = await self._get_advanced_stats_probability(game, team_name, is_home)
if advanced_stats_prob is not None:
    probabilities["advanced_stats"] = advanced_stats_prob

# Mean is automatically recalculated
```

## Performance Considerations

- **Async**: All external API calls are async, won't block
- **Graceful Fallback**: If any model fails, system continues with others
- **Caching**: Consider caching API results (see `EXAMPLE_MODELS.py`)
- **Timeouts**: Implement request timeouts to prevent hanging
- **Rate Limits**: Monitor API rate limits, especially for Vegas odds

## Files Modified/Created

| File | Change | Impact |
|------|--------|--------|
| `backend/services/aai/recommendations.py` | Added ExternalOddsAggregator, modified generate() | Core functionality |
| `frontend/src/pages/AAIBetsPage.jsx` | Added external odds rendering | UI display |
| `frontend/src/pages/AAIBetsPage.css` | Added confidence column & odds styles | UI styling |
| `backend/services/aai/EXTERNAL_MODELS_GUIDE.md` | Integration documentation | Reference |
| `backend/services/aai/EXAMPLE_MODELS.py` | Ready-to-use implementations | Integration templates |
| `test_external_odds.py` | Aggregation logic demo | Testing |

## Next Steps

1. **Choose Models**: Decide which external sources to integrate
2. **Get API Keys**: Sign up for OddsAPI, Elo service, etc.
3. **Implement Methods**: Fill in the placeholder methods
4. **Add Error Handling**: Wrap API calls with try/except
5. **Test Integration**: Use test_external_odds.py as template
6. **Monitor Performance**: Check API response times and reliability
7. **Adjust Weights**: Backtest different blend ratios

## Quick Start: Enable Vegas Odds

1. Sign up at https://the-odds-api.com/
2. Get your API key
3. Add to `.env`: `ODDSAPI_KEY=your_key_here`
4. Implement `_get_vegas_implied_probability()` (see EXAMPLE_MODELS.py)
5. Restart backend
6. Check UI for Vegas odds in external models breakdown

## Questions?

Refer to:
- `EXTERNAL_MODELS_GUIDE.md` - Detailed integration guide
- `EXAMPLE_MODELS.py` - Code examples for each model
- `test_external_odds.py` - Working test demonstrating aggregation
