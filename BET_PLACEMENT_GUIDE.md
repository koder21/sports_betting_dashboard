# Bet Placement System - Complete Implementation Guide

## Overview

Your betting dashboard now has a complete bet placement system with the following features:

1. ✅ **Place AAI Recommendations** - Convert AI picks to "pending" active bets with custom stake/odds
2. ✅ **Custom Bet Builder** - Build singles and parlays from any upcoming games
3. ✅ **Parlay Auto-Calculation** - Combined odds calculated automatically
4. 🔄 **PROP Bets Integration** - Ready for implementation (see PROP_BETS_SETUP.md)

---

## System Components

### Backend Services

#### BetPlacementService (`backend/services/bet_placement.py`)
**Purpose**: Core business logic for converting picks to pending bets

**Methods**:
- `place_aai_single(game_id, pick, confidence, stake, odds, reason, sport)` → Returns bet with ID and potential win amount
- `place_aai_parlay(legs, stake, sport)` → Returns parlay with auto-calculated odds
- `build_custom_single(game_id, pick, stake, odds, notes)` → Place custom single
- `build_custom_parlay(legs, stake, notes)` → Place custom parlay with auto-odds

**Features**:
- All bets stored as "pending" status
- Parlay IDs auto-generated (UUID-based)
- Confidence scores preserved in reason/notes
- Full transaction support with rollback on error

### Backend API Routes

#### Endpoints (`backend/routers/bet_placement.py`)

**Place AAI Single Pick**
```
POST /bets/place-aai-single
Content-Type: application/json

{
  "game_id": "401810616",
  "pick": "Lakers -5",
  "confidence": 65,
  "combined_confidence": 72,
  "stake": 100,
  "odds": 1.95,
  "reason": "Form analysis shows strong defense",
  "sport": "NBA"
}

Response: {
  "success": true,
  "bet_id": 1,
  "game_id": "401810616",
  "pick": "Lakers -5",
  "odds": 1.95,
  "stake": 100,
  "confidence": 72,
  "potential_win": 95,
  "status": "pending"
}
```

**Place AAI Parlay**
```
POST /bets/place-aai-parlay
Content-Type: application/json

{
  "legs": [
    {
      "game_id": "401810616",
      "pick": "Lakers -5",
      "odds": 1.95,
      "confidence": 65
    },
    {
      "game_id": "401810617",
      "pick": "Celtics +3",
      "odds": 2.10,
      "confidence": 58
    }
  ],
  "stake": 50,
  "sport": "NBA"
}

Response: {
  "success": true,
  "parlay_id": "parlay_a1b2c3d4",
  "bet_id": 2,
  "legs": 2,
  "parlay_odds": 4.095,
  "stake": 50,
  "potential_win": 204.75,
  "status": "pending"
}
```

**Build Custom Single**
```
POST /bets/build-custom-single
Content-Type: application/json

{
  "game_id": "401810616",
  "pick": "Lakers -5",
  "stake": 100,
  "odds": 1.95,
  "notes": "Strong defensive matchup"
}

Response: {
  "success": true,
  "bet_id": 3,
  "pick": "Lakers -5",
  "odds": 1.95,
  "stake": 100,
  "potential_win": 95,
  "status": "pending"
}
```

**Build Custom Parlay**
```
POST /bets/build-custom-parlay
Content-Type: application/json

{
  "legs": [
    {
      "game_id": "401810616",
      "pick": "Lakers -5",
      "odds": 1.95
    },
    {
      "game_id": "401810617",
      "pick": "Celtics +3",
      "odds": 2.10
    }
  ],
  "stake": 50,
  "notes": "Strong defensive matchups"
}

Response: {
  "success": true,
  "parlay_id": "parlay_b2c3d4e5",
  "bet_id": 4,
  "legs": 2,
  "parlay_odds": 4.095,
  "stake": 50,
  "potential_win": 204.75,
  "status": "pending"
}
```

### Frontend Components

#### BetPlacementModal (`frontend/src/components/BetPlacementModal.jsx`)
**Purpose**: Modal dialog for placing a single AAI recommendation as a bet

**Props**:
- `bet` - The AAI pick to place
- `isOpen` - Boolean to show/hide modal
- `onClose` - Callback when modal closes
- `onSuccess` - Callback when bet placed successfully

**Features**:
- Display pick details (matchup, confidence, reason)
- Adjustable stake ($) and odds
- Real-time potential win calculation
- Error handling with user feedback

**Usage**:
```jsx
<BetPlacementModal 
  bet={selectedBet}
  isOpen={showPlacementModal}
  onClose={closeBetPlacementModal}
  onSuccess={handleBetPlacedSuccess}
/>
```

#### CustomBetBuilder (`frontend/src/components/CustomBetBuilder.jsx`)
**Purpose**: Modal for building custom singles and parlays from upcoming games

**Props**:
- `games` - Array of upcoming games to select from
- `isOpen` - Boolean to show/hide modal
- `onClose` - Callback when modal closes

**Features**:
- Toggle between Single and Parlay modes
- Select games by clicking cards
- Customize pick and odds for each leg
- Real-time parlay odds and potential win calculation
- Notes field for documenting reasoning
- Input validation (1 game for single, 2+ for parlay)

**Usage**:
```jsx
<CustomBetBuilder 
  games={data?.upcoming_games || []}
  isOpen={showCustomBuilder}
  onClose={closeCustomBuilder}
/>
```

#### AAIBetsPage Integration (`frontend/src/pages/AAIBetsPage.jsx`)
**Changes**:
- Import both modal components
- Add state for selected bet and modal visibility
- Add "Place Bet" button to each AAI single
- Add "Build Custom Bet" button in new section
- Manage modal open/close and success callbacks

**New Functions**:
- `openBetPlacementModal(bet)` - Open modal with selected bet
- `closeBetPlacementModal()` - Close bet placement modal
- `handleBetPlacedSuccess(result)` - Handle successful bet placement
- `openCustomBuilder()` - Open custom bet builder
- `closeCustomBuilder(result)` - Close custom builder

---

## Database Schema

### Existing bets Table
```sql
CREATE TABLE bets (
  id INTEGER PRIMARY KEY,
  placed_at DATETIME,
  sport_id INTEGER,
  game_id TEXT,
  player_id INTEGER,
  raw_text TEXT,
  stake REAL,
  odds REAL,
  bet_type TEXT,  -- 'single' or 'parlay'
  selection TEXT,
  status TEXT,  -- 'pending', 'active', 'won', 'lost', 'cancelled'
  parlay_id TEXT,  -- UUID for grouping parlay legs
  reason TEXT,  -- Store confidence/analysis info
  profit REAL
);
```

**Status Values**:
- `pending` - Newly placed, not yet finalized
- `active` - Bet is live, waiting for game result
- `won` - Bet won ✅
- `lost` - Bet lost ❌
- `cancelled` - Bet cancelled

**Parlay Structure**:
Each leg of a parlay has its own row with:
- Same `parlay_id` (UUID)
- `bet_type` = "parlay"
- Individual `odds` for that leg
- `reason` field stores individual leg confidence

---

## Workflow Examples

### Example 1: Place AAI Recommendation

1. User clicks "Calculate Odds" on AAI page
2. Fresh data scraped, recommendations calculated
3. User sees "💰 Place Bet" button on a single
4. Clicks button → BetPlacementModal opens
5. User adjusts stake from $50 to $100
6. Modal shows potential win: $95
7. User clicks "Place Bet"
8. Bet created in database with status="pending"
9. Modal closes, user sees confirmation

**Database Result**:
```
id: 1
placed_at: 2025-01-15 14:32:00
game_id: "401810616"
pick: "Lakers -5"
stake: 100
odds: 1.95
bet_type: "single"
status: "pending"
reason: "AAI - Form analysis shows strong defense - Confidence: 72%"
```

### Example 2: Build Custom Parlay

1. User clicks "Build Custom Bet" button
2. CustomBetBuilder modal opens
3. User selects Parlay mode (toggle)
4. Clicks on Game #1: Lakers @ Celtics
   - Selects "Lakers -5"
   - Sets odds to 1.95
5. Clicks on Game #2: Warriors @ Suns
   - Selects "Warriors -3.5"
   - Sets odds to 2.10
6. Modal shows:
   - Legs: 2
   - Parlay Odds: 4.095x
   - Stake: $50
   - Potential Win: $204.75
7. Adds note: "Back-to-back road teams struggling"
8. Clicks "Build & Place Bet"
9. System creates parlay with 2 legs, stores with parlay_id

**Database Result**:
```
id: 2 (first leg)
parlay_id: "parlay_a1b2c3d4"
game_id: "401810616"
pick: "Lakers -5"
odds: 1.95
stake: 50  (total parlay stake)
bet_type: "parlay"
status: "pending"

id: 3 (second leg)
parlay_id: "parlay_a1b2c3d4"
game_id: "401810617"
pick: "Warriors -3.5"
odds: 2.10
stake: 50  (total parlay stake)
bet_type: "parlay"
status: "pending"
```

---

## PROP Bets Integration

Currently, the system handles game picks (spreads, moneylines, totals).

**To add PROP bets** (player props like Points Over/Under):
1. Set up The Odds API (see PROP_BETS_SETUP.md)
2. Create props table in database
3. Add prop scraping to FreshDataScraper
4. Modify CustomBetBuilder to show player props
5. Modify BetPlacementService to handle prop odds

**Next Steps for PROP Support**:
```
1. Sign up: https://theoddsapi.com/
2. Get API key
3. Add to .env: ODDS_API_KEY=your_key
4. Uncomment prop fetching in fresh_data_scraper.py
5. Test prop endpoints returning data
6. Update frontend to display props
```

---

## Error Handling

### Error Scenarios

**Insufficient Funds** (Future)
```json
{
  "success": false,
  "error": "Account balance $50 < requested stake $100"
}
```

**Invalid Game ID**
```json
{
  "success": false,
  "error": "Game 401810999 not found"
}
```

**Parlay Requires 2+ Legs**
```json
{
  "success": false,
  "error": "Parlay must have at least 2 legs"
}
```

**Invalid Odds**
```json
{
  "success": false,
  "error": "Odds must be greater than 1.01"
}
```

---

## Testing

### Manual Testing Checklist

- [ ] Place single AAI bet with default stake
- [ ] Place single AAI bet with custom stake ($150)
- [ ] Place single AAI bet with custom odds (1.75)
- [ ] Verify bet appears in database with status="pending"
- [ ] Build custom single (select 1 game, place bet)
- [ ] Build custom parlay (select 2 games, verify parlay odds)
- [ ] Build custom parlay (select 3 games, verify combined odds)
- [ ] Add notes to custom bet
- [ ] Verify all bets stored correctly in database
- [ ] Test error handling (invalid inputs)
- [ ] Verify modal closes after success
- [ ] Verify modal closes on cancel

### API Testing (curl)

```bash
# Place AAI Single
curl -X POST http://localhost:8000/bets/place-aai-single \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "401810616",
    "pick": "Lakers -5",
    "confidence": 65,
    "combined_confidence": 72,
    "stake": 100,
    "odds": 1.95,
    "reason": "Test bet",
    "sport": "NBA"
  }'

# Build Custom Parlay
curl -X POST http://localhost:8000/bets/build-custom-parlay \
  -H "Content-Type: application/json" \
  -d '{
    "legs": [
      {"game_id": "401810616", "pick": "Lakers -5", "odds": 1.95},
      {"game_id": "401810617", "pick": "Celtics +3", "odds": 2.10}
    ],
    "stake": 50,
    "notes": "Test parlay"
  }'
```

---

## Monitoring & Analytics

### Tracking Pending Bets
```sql
SELECT COUNT(*) FROM bets WHERE status = 'pending';
SELECT SUM(stake) FROM bets WHERE status = 'pending';
SELECT AVG(odds) FROM bets WHERE status = 'pending' AND bet_type = 'single';
```

### Parlay Analysis
```sql
SELECT parlay_id, COUNT(*) as leg_count, SUM(stake) as total_stake
FROM bets 
WHERE bet_type = 'parlay' AND status = 'pending'
GROUP BY parlay_id;
```

### Win Rate by Source
```sql
SELECT reason, 
  COUNT(*) as total,
  SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
  ROUND(100.0 * SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM bets
GROUP BY reason;
```

---

## Next Steps

### Immediate (Priority: HIGH)
- [ ] Test all endpoints manually
- [ ] Verify database inserts
- [ ] Test error scenarios
- [ ] Add toast notifications for success/error

### Short Term (Priority: HIGH)
- [ ] Implement PROP bets (see PROP_BETS_SETUP.md)
- [ ] Add props to CustomBetBuilder
- [ ] Integrate props into AAI recommendations

### Medium Term (Priority: MEDIUM)
- [ ] Add bet history page showing pending/won/lost
- [ ] Add tracking of actual vs predicted odds
- [ ] Implement automatic bet grading when games complete
- [ ] Add ROI tracking by sport/league

### Long Term (Priority: LOW)
- [ ] Implement bankroll management
- [ ] Add Kelly Criterion calculations
- [ ] Implement automatic lineup optimizer
- [ ] Add push notifications for line movements

---

## Support & Troubleshooting

### Common Issues

**"Cannot place bet: Game not found"**
- Ensure game_id is valid (check /games endpoint)
- Ensure fresh data has been scraped (click "Recalculate")

**"Modal won't close after clicking Place Bet"**
- Check browser console for API errors
- Verify backend is running
- Check network tab for failed requests

**Custom bet builder not showing games**
- Ensure upcoming_games is returned from AAI endpoint
- Check that games have required fields: game_id, home, away, start_time

**Parlay odds not calculating correctly**
- Verify each leg has valid odds > 1.01
- Check that multiplication is working: 1.95 × 2.10 = 4.095

### Debug Commands

```bash
# Check pending bets
curl http://localhost:8000/bets/status/pending

# Get bet details
curl http://localhost:8000/bets/{bet_id}

# List all bets by sport
curl http://localhost:8000/bets/sport/NBA
```

---

## Code Organization

```
backend/
  services/
    bet_placement.py  (BetPlacementService - 230+ lines)
  routers/
    bet_placement.py  (REST API - 120+ lines)

frontend/
  components/
    BetPlacementModal.jsx  (Place single bet UI)
    CustomBetBuilder.jsx   (Build parlay/single UI)
  styles/
    BetPlacementModal.css  (Modal styling)
    CustomBetBuilder.css   (Builder styling)
  pages/
    AAIBetsPage.jsx  (Integration of both components)
```

---

## Summary

You now have a complete bet placement system that allows:

1. ✅ Converting AAI recommendations to "pending" active bets
2. ✅ Building custom singles from any upcoming game
3. ✅ Building custom parlays with auto-calculated odds
4. ✅ Tracking all bets with confidence/reason info
5. 🔄 Ready for PROP bets integration

**All bets start with status="pending"** and can be manually graded as won/lost or automatically graded when games complete.

---

**Ready to go live!** Test all endpoints, then start placing bets from your AAI recommendations.
