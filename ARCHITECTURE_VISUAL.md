# External Model Aggregation - Visual Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AAI BETS RECOMMENDATION ENGINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ For each upcoming game (next 24 hours)                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ FORM-BASED CONFIDENCE (Existing Logic)                              │  │
│  │ ├─ Query GameResult for home team: W-L record (past 5 games)        │  │
│  │ ├─ Query GameResult for away team: W-L record (past 5 games)        │  │
│  │ ├─ Calculate: home_win_rate - away_win_rate = diff                 │  │
│  │ ├─ Confidence = 0.5 + abs(diff)/2 (clamped 51%-85%)                │  │
│  │ └─ Result: 58% (for this example)                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ EXTERNAL ODDS AGGREGATION (New: ExternalOddsAggregator)             │  │
│  │                                                                      │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ Model 1: Home Field Advantage (ACTIVE)                         │ │  │
│  │ │ ├─ Empirical: Home teams win ~54% across sports               │ │  │
│  │ │ ├─ Static value: 54%                                           │ │  │
│  │ │ └─ Always available                                            │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ Model 2: Elo Ratings (PLACEHOLDER - Ready to integrate)        │ │  │
│  │ │ ├─ Fetch: custom Elo service                                   │ │  │
│  │ │ ├─ Convert: 1 / (1 + 10^(-elo_diff/400))                       │ │  │
│  │ │ ├─ Status: Returns None (skipped if not implemented)           │ │  │
│  │ │ └─ Example: Would return 56%                                   │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ Model 3: Vegas Implied Odds (PLACEHOLDER - Ready to integrate) │ │  │
│  │ │ ├─ Fetch: OddsAPI, TheOddsAPI, or sportsbook API              │ │  │
│  │ │ ├─ Parse: DraftKings/FanDuel moneyline (e.g., -130)            │ │  │
│  │ │ ├─ Convert: |ML| / (|ML| + 100) = 56.5%                        │ │  │
│  │ │ ├─ Status: Returns None (skipped if not implemented)           │ │  │
│  │ │ └─ Example: Would return 55%                                   │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ Model 4: Predictive ML Model (PLACEHOLDER - Ready to integrate)│ │  │
│  │ │ ├─ Fetch: Custom ML model service endpoint                     │ │  │
│  │ │ ├─ Send: Game/team features as JSON                            │ │  │
│  │ │ ├─ Get: win_probability from response                          │ │  │
│  │ │ ├─ Status: Returns None (skipped if not implemented)           │ │  │
│  │ │ └─ Example: Would return 61%                                   │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │ AGGREGATION:                                                       │  │
│  │ ├─ Collect all non-None probabilities                            │  │
│  │ ├─ Calculate mean: (54%) / 1 = 54.0%                             │  │
│  │ └─ Return: {home_advantage: 54%, mean: 54%}                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ CONFIDENCE BLENDING (50% Form + 50% External)                        │  │
│  │ ├─ Form Confidence: 58%                                             │  │
│  │ ├─ External Mean: 54%                                               │  │
│  │ ├─ Blended = (58% + 54%) / 2 = 56%                                 │  │
│  │ └─ Result: {form: 58%, blended: 56%, odds_dict: {...}}             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ SORT & RANK                                                         │  │
│  │ └─ Sort by combined_confidence (blended value)                      │  │
│  │ └─ Return top 5 singles                                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ BUILD PARLAYS                                                       │  │
│  │ └─ Combine top singles into 2-leg and 3-leg parlays                │  │
│  │ └─ Parlay confidence = leg1 * leg2 * leg3                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ RETURN JSON                                                         │  │
│  │ {                                                                   │  │
│  │   "singles": [{pick, confidence, combined_confidence, external_odds}],│ │
│  │   "parlays": [{legs, confidence, combined_confidence}],            │  │
│  │   "generated_at": "2026-02-10T12:00:00",                           │  │
│  │   "disclaimer": "..."                                              │  │
│  │ }                                                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                            ↓                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                            ↓
                        ┌─────────┐
                        │ Frontend│
                        └─────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │  Display:                             │
        │  • Form: 58% (green)                  │
        │  • Blended: 56% (blue)                │
        │  • Expandable: Show all models        │
        │    - home_advantage: 54%              │
        │    - mean: 54%                        │
        └───────────────────────────────────────┘
```

## Current State (Home Advantage Model Active)

```
INPUT: Game 401772988
       Seattle @ New England
       Pick: Seattle Seahawks (home)

FORM ANALYSIS:
  ✓ Query GameResult for Seattle (home team)
  ✓ Query GameResult for New England (away team)
  ✓ Calculate win rate difference
  → Form Confidence: 58%

EXTERNAL AGGREGATION:
  ✓ Model 1 (Home Advantage): 54% ← ACTIVE
    Returns: 54%
  
  ○ Model 2 (Elo): Returns None (not implemented)
  ○ Model 3 (Vegas): Returns None (not implemented)
  ○ Model 4 (ML Model): Returns None (not implemented)
  
  → Mean Calculation: (54%) / 1 = 54%

BLENDING:
  Form: 58%
  External Mean: 54%
  Blended (50/50): (58 + 54) / 2 = 56%

OUTPUT JSON:
{
  "pick": "Seattle Seahawks",
  "confidence": 58.0,           ← Form only
  "combined_confidence": 56.0,  ← Form + External
  "external_odds": {
    "home_advantage": 54.0,
    "mean": 54.0
  }
}

FRONTEND DISPLAY:
  ┌─ Seattle Seahawks           Form: 58%
  │  Seattle @ New England      Blended: 56%
  │  Recent form: ...
  │  ▼ External Models (1)
  │    • home_advantage: 54.0%
  │    • mean: 54.0%
```

## After Integrating Vegas Odds (Example)

```
EXTERNAL AGGREGATION:
  ✓ Model 1 (Home Advantage): 54%
  ✓ Model 2 (Vegas Implied): 55%  ← NEW!
  ○ Model 3 (Elo): Returns None
  ○ Model 4 (ML Model): Returns None
  
  → Mean Calculation: (54 + 55) / 2 = 54.5%

BLENDING:
  Form: 58%
  External Mean: 54.5%
  Blended (50/50): (58 + 54.5) / 2 = 56.25%

OUTPUT JSON:
{
  "pick": "Seattle Seahawks",
  "confidence": 58.0,
  "combined_confidence": 56.25,  ← Updated!
  "external_odds": {
    "home_advantage": 54.0,
    "vegas": 55.0,              ← NEW!
    "mean": 54.5                ← Updated!
  }
}

FRONTEND DISPLAY:
  ┌─ Seattle Seahawks           Form: 58%
  │  Seattle @ New England      Blended: 56.3%
  │  Recent form: ...
  │  ▼ External Models (2)
  │    • home_advantage: 54.0%
  │    • vegas: 55.0%            ← NEW!
  │    • mean: 54.5%             ← Updated!
```

## Integration Workflow

```
Step 1: Choose Model
  ┌─ Vegas (OddsAPI) - Easiest
  ├─ Elo Ratings - Good data
  ├─ Custom ML - Most powerful
  └─ Multiple - Best results

Step 2: Get Credentials
  └─ Sign up, get API key, add to .env

Step 3: Implement Method
  ├─ Copy from EXAMPLE_MODELS.py
  ├─ Fill in API client call
  ├─ Add error handling
  └─ Test with sample data

Step 4: Test
  ├─ Run test_external_odds.py
  ├─ Check backend logs
  └─ Verify frontend shows new model

Step 5: Monitor
  ├─ Check API response times
  ├─ Monitor rate limits
  └─ Watch confidence changes
```

## Confidence Score Interpretation

```
Form Confidence (58%) → Team Form
├─ Based on recent win rate
├─ Only data-driven from actual games
└─ Range: 51% (slight edge) to 85% (dominant)

External Odds Mean (54%) → Market/Model Average
├─ Home advantage (always active)
├─ Vegas/ML/Elo (when integrated)
└─ Range: 0% to 100%

Blended Confidence (56%) → Final Recommendation
├─ 50% weight to form analysis
├─ 50% weight to external models
├─ Balances data with market wisdom
└─ What appears in UI/API

Weight Adjustment:
└─ Want to trust form more? Use 60% form, 40% external
└─ Want to trust models more? Use 40% form, 60% external
└─ Disable external? Use form_confidence directly
```

## Quick Integration Path

```
TODAY (Already Done)
  ✅ System architecture in place
  ✅ Home advantage model active (54%)
  ✅ Frontend displays dual confidence
  ✅ Blending logic working
  ✅ Documentation complete

WEEK 1 (Add Vegas)
  → Sign up at OddsAPI (free tier: 500 requests/month)
  → Implement _get_vegas_implied_probability()
  → Test with test_external_odds.py
  → Monitor frontend for new scores

WEEK 2 (Add Elo)
  → Choose Elo source (custom provider, internal model, etc.)
  → Implement _get_elo_probability()
  → Cache results (optional: 60 min TTL)
  → Backtest against historical data

WEEK 3+ (Add ML Model)
  → Deploy ML service or use existing
  → Implement _get_predictive_model_probability()
  → Fine-tune blend weights based on results
  → Monitor prediction accuracy
```
