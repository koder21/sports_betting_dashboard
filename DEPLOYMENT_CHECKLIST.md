# 🚀 Deployment Checklist - Bet Placement System

## Pre-Deployment Verification

### ✅ Code Quality
- [x] All 6 new files created without syntax errors
- [x] All 5 modified files properly integrated
- [x] Imports are correct and circular-dependency-free
- [x] Type hints present on all functions
- [x] Error handling implemented for all endpoints
- [x] Database transactions use proper rollback

### ✅ Backend Components
- [x] `BetPlacementService` class complete (230+ lines)
  - [x] `place_aai_single()` implemented
  - [x] `place_aai_parlay()` implemented
  - [x] `build_custom_single()` implemented
  - [x] `build_custom_parlay()` implemented
  - [x] All methods have proper error handling
  - [x] All methods return consistent response format

- [x] `bet_placement.py` router complete (120+ lines)
  - [x] 4 POST endpoints defined
  - [x] Pydantic schemas for request validation
  - [x] Response schemas defined
  - [x] Error responses (400, 500) implemented
  - [x] Dependency injection setup

- [x] `main.py` updated
  - [x] Import added: `from backend.routers import bet_placement`
  - [x] Router registered: `app.include_router(bet_placement.router)`

- [x] `__init__.py` updated
  - [x] `bet_placement` added to imports
  - [x] `bet_placement` added to __all__

### ✅ Frontend Components
- [x] `BetPlacementModal.jsx` created (90+ lines)
  - [x] All props handled correctly
  - [x] Modal overlay with click-outside close
  - [x] Input validation
  - [x] Real-time calculation
  - [x] Error display
  - [x] Loading state

- [x] `CustomBetBuilder.jsx` created (200+ lines)
  - [x] Single/Parlay toggle
  - [x] Game selection with click handlers
  - [x] Per-game pick/odds customization
  - [x] Parlay odds calculation
  - [x] Input validation
  - [x] Error handling

- [x] `AAIBetsPage.jsx` updated
  - [x] Imports added
  - [x] Modal state management
  - [x] "Place Bet" buttons added
  - [x] "Build Custom Bet" button added
  - [x] Modal components rendered
  - [x] Success callbacks implemented

- [x] CSS styling
  - [x] BetPlacementModal.css complete (170+ lines)
  - [x] CustomBetBuilder.css complete (250+ lines)
  - [x] AAIBetsPage.css buttons added
  - [x] All animations and transitions
  - [x] Responsive design

### ✅ Documentation
- [x] `BET_PLACEMENT_GUIDE.md` (1200+ lines) - Complete
  - [x] System architecture documented
  - [x] All 4 endpoints documented with examples
  - [x] Both components documented with props
  - [x] Database schema explained
  - [x] 2 detailed workflow examples
  - [x] Error scenarios documented
  - [x] Testing checklist provided
  - [x] Troubleshooting guide included

- [x] `PROP_BETS_SETUP.md` (250+ lines) - Complete
  - [x] The Odds API recommendation
  - [x] Setup instructions
  - [x] Cost analysis
  - [x] Alternative solutions
  - [x] Integration points

- [x] `SESSION_SUMMARY.md` (400+ lines) - Complete
  - [x] What was built documented
  - [x] File inventory listed
  - [x] Technical details explained
  - [x] Workflow examples provided
  - [x] Testing instructions included

- [x] `QUICK_REFERENCE.md` - Updated
  - [x] Bet placement endpoints added
  - [x] API examples added
  - [x] Feature summary updated

---

## Testing Checklist

### Unit Tests
- [ ] BetPlacementService.place_aai_single() with valid data
- [ ] BetPlacementService.place_aai_parlay() with 2 legs
- [ ] BetPlacementService.build_custom_single() 
- [ ] BetPlacementService.build_custom_parlay() with 3 legs
- [ ] Error handling for missing game_id
- [ ] Error handling for invalid odds
- [ ] Parlay odds calculation accuracy

### Integration Tests
- [ ] POST /bets/place-aai-single with curl
- [ ] POST /bets/place-aai-parlay with curl
- [ ] POST /bets/build-custom-single with curl
- [ ] POST /bets/build-custom-parlay with curl
- [ ] Verify bets in database with correct status
- [ ] Verify parlay_id grouping in database
- [ ] Verify reason/notes stored correctly

### Frontend Tests
- [ ] Click "Calculate Odds" on AAI page
- [ ] See "💰 Place Bet" buttons on singles
- [ ] Click "Place Bet" button → modal opens
- [ ] Modal shows bet details correctly
- [ ] Adjust stake and see calculation update
- [ ] Adjust odds and see calculation update
- [ ] Click "Place Bet" → success
- [ ] Click "🎯 Build Custom Bet" button
- [ ] CustomBetBuilder modal opens
- [ ] Select 1 game in Single mode
- [ ] Select 2+ games in Parlay mode
- [ ] Parlay odds calculated correctly
- [ ] Click "Build & Place Bet" → success

### Error Scenarios
- [ ] Place bet with invalid game_id → error message
- [ ] Place bet with odds < 1.01 → error message
- [ ] Parlay with only 1 leg → error message
- [ ] Network timeout → error handling
- [ ] Database error → transaction rollback

### Database Verification
```bash
# Check pending bets
sqlite3 sports_intel.db "SELECT COUNT(*) FROM bets WHERE status='pending';"

# Check parlay grouping
sqlite3 sports_intel.db "SELECT parlay_id, COUNT(*) FROM bets WHERE bet_type='parlay' GROUP BY parlay_id;"

# Check confidence storage
sqlite3 sports_intel.db "SELECT reason FROM bets WHERE status='pending' LIMIT 3;"
```

---

## Deployment Steps

### 1. Pre-Deployment
```bash
# Verify no syntax errors
cd /Users/dakotanicol/sports_betting_dashboard
python -m py_compile backend/services/bet_placement.py
python -m py_compile backend/routers/bet_placement.py

# Check imports
python -c "from backend.services.bet_placement import BetPlacementService"
python -c "from backend.routers import bet_placement"

# Verify frontend syntax
npm run lint (if linter configured)
```

### 2. Database Check
```bash
# Ensure bets table exists
sqlite3 sports_intel.db ".schema bets"

# Verify required columns
sqlite3 sports_intel.db "PRAGMA table_info(bets);"
```

### 3. Backend Server Start
```bash
cd backend
python -m uvicorn main:app --reload

# Should see:
# Uvicorn running on http://127.0.0.1:8000
# And router registered: bet-placement
```

### 4. Frontend Server Start
```bash
cd frontend
npm run dev

# Should see:
# VITE v... ready in ... ms
# ➜  Local: http://localhost:5173
```

### 5. Manual Testing
- Open http://localhost:5173 in browser
- Navigate to AAI page
- Click "Calculate Odds"
- Verify fresh data loads
- Click "Place Bet" on a single
- Place a test bet
- Check database for new record
- Test custom builder

### 6. Production Deployment
```bash
# Build frontend
cd frontend
npm run build
# Creates dist/ folder

# Deploy to production server
# (e.g., nginx, Apache, cloud platform)

# Start backend
cd backend
python -m gunicorn main:app -w 4 -b 0.0.0.0:8000
```

---

## Post-Deployment Verification

### ✅ Health Checks
- [ ] Backend server is running (curl localhost:8000/health)
- [ ] Frontend loads without 404 errors
- [ ] Network requests show 200 status codes
- [ ] No JavaScript errors in console
- [ ] No Python errors in backend logs

### ✅ Feature Verification
- [ ] AAI page calculates odds
- [ ] Place Bet button appears
- [ ] Modal opens with correct data
- [ ] Calculations show correct values
- [ ] Bets are stored in database
- [ ] Status shows "pending"
- [ ] Custom builder works for singles
- [ ] Custom builder works for parlays
- [ ] Parlay odds calculated correctly

### ✅ Database Verification
- [ ] New bets appear in database
- [ ] Parlay IDs are UUIDs
- [ ] Confidence/reason preserved
- [ ] Status is "pending"
- [ ] Game IDs match AAI picks

### ✅ Error Handling
- [ ] Invalid inputs show error message
- [ ] Network errors handled gracefully
- [ ] Database errors don't crash app
- [ ] Modals close properly

---

## Rollback Plan

If issues occur:

1. **Frontend Issue**
   ```bash
   # Revert AAIBetsPage.jsx to backup
   git checkout frontend/src/pages/AAIBetsPage.jsx
   # Remove new components from folder
   rm frontend/src/components/BetPlacementModal.jsx
   rm frontend/src/components/CustomBetBuilder.jsx
   ```

2. **Backend Issue**
   ```bash
   # Revert main.py and __init__.py
   git checkout backend/main.py
   git checkout backend/routers/__init__.py
   # Remove new service and router
   rm backend/services/bet_placement.py
   rm backend/routers/bet_placement.py
   ```

3. **Database Issue**
   ```bash
   # Backup current database
   cp sports_intel.db sports_intel.db.backup-$(date +%s)
   # Restore from previous backup
   ```

---

## Monitoring (After Deployment)

### Key Metrics
- Number of pending bets created
- Average parlay size (legs)
- Error rate on placement
- Database insert latency
- Frontend load times

### Commands to Monitor
```bash
# Count pending bets over time
watch 'sqlite3 sports_intel.db "SELECT COUNT(*) FROM bets WHERE status=\"pending\" AND placed_at > datetime(\"now\", \"-1 hour\");"'

# Check error logs
tail -f backend/logs/errors.log

# Monitor frontend console
# (Check browser Dev Tools)
```

---

## Sign-Off Checklist

- [ ] All code reviewed and approved
- [ ] All tests passing
- [ ] All documentation complete
- [ ] Database backups created
- [ ] Rollback plan documented
- [ ] Team notified of deployment
- [ ] Monitoring configured
- [ ] Deployment time scheduled
- [ ] Stakeholders informed

---

## Support Contacts

**For Help With**:
- **Backend Issues**: Check backend/logs/ and Python error messages
- **Frontend Issues**: Check browser console and network tab
- **Database Issues**: Verify sports_intel.db is not locked
- **API Issues**: See curl examples in BET_PLACEMENT_GUIDE.md
- **PROP Integration**: Read PROP_BETS_SETUP.md

---

## Success Criteria

✅ **Deployment is successful if**:
1. All 4 endpoints respond to requests
2. Bets are stored in database with correct status
3. Parlay odds are calculated correctly
4. Modals open and close without errors
5. All required fields are populated
6. Error handling works for invalid inputs
7. No JavaScript or Python errors in logs
8. Frontend loads without 404s
9. Users can place bets from AAI page
10. Users can build custom parlays

---

**Ready to deploy!** Follow the steps above, verify all checks, then you're live. 🚀
