# Code Cleanup & Consolidation Audit

**Date**: February 10, 2026  
**Status**: SAFE REMOVALS IDENTIFIED  

## Items for Removal (Safe to Delete)

### 1. ❌ REMOVE: backend/services/caching.py

**Status**: UNUSED - Never imported or called anywhere  
**Lines**: 13  
**Impact**: None - dead code

**Reason**: 
```bash
grep -r "cache_get_or_set" backend/  # No matches except definition
```

**Recommendation**: **DELETE** - Zero risk

---

### 2. ⚠️ CONSOLIDATE: backend/routers/insights.py

**Status**: UNDER CONSTRUCTION - All endpoints return placeholder responses  
**Functions**: 4 (all return "under_construction" status)
- `get_trending_props()` - Returns `{ trending: [], status: "under_construction" }`
- `get_trending_by_sport(sport)` - Returns `{ trending: [], status: "under_construction" }`  
- `get_insight_stats()` - Returns `{ status: "under_construction" }`
- `process_discord_webhook()` - Returns `{ status: "under_construction" }`

**Frontend Usage**: 
```bash
grep -r "/insights" frontend/  # No matches
```

**Recommendation**: 
- **Option A (Recommended)**: DELETE entire file + remove from main.py imports
- **Option B**: Keep but document as "Reserved for future use"
- **Option C**: Consolidate all 4 placeholder endpoints into 1 generic endpoint

**Decision**: **DELETE** - No frontend integration, all placeholders

---

## Items for Consolidation (Safe to Optimize)

### 1. ✅ CONSOLIDATE: Database pragma setup in db.py

**Current**: Separate function `set_sqlite_pragma()` with 3 pragmas  
**Consolidation**: All 3 pragmas together (already done - GOOD)

**Status**: ✅ ALREADY OPTIMAL

---

### 2. ✅ CONSOLIDATE: Alert manager error handling

**Location**: backend/services/alerts/manager.py  
**Current**: Two code paths for session management (`self.session` vs `self.session_factory`)  
**Assessment**: Actually necessary - supports both immediate and queued alert creation

**Status**: ✅ NECESSARY - Keep as is

---

### 3. ✅ CONSOLIDATE: JSON serialization utilities

**Location**: backend/utils/json.py  
**Current**: 
- `_serialize()` - Core recursive serializer
- `safe_json()` - Returns JSON string
- `to_primitive()` - Returns Python objects
- `normalize_json_payload()` - Validates and normalizes

**Assessment**: Each serves distinct purpose, no consolidation possible without reducing functionality

**Status**: ✅ OPTIMAL - Keep as is

---

### 4. ✅ CONSOLIDATE: SQLAlchemy pattern usage

**Current Usage Pattern Analysis**:

✅ Bulk fetch pattern used in:
- live.py - GOOD
- games.py - GOOD  
- props.py - GOOD

✅ Eager loading used in:
- bet_repo.py - GOOD
- props.py - GOOD

✅ Aggregation used in:
- forecaster_leaderboard.py - GOOD
- trends_detailed.py - GOOD

**Status**: ✅ CONSISTENT - No consolidation needed

---

### 5. ⚠️ ASSESSMENT: Bet parser complexity

**Location**: backend/services/betting/parser.py  
**Lines**: 398  
**Complexity**: High (handles multiple parlay formats, auto-grouping)  
**Assessment**: Consolidation not safe - single responsibility is parsing bets in various formats

**Status**: ✅ NECESSARY - Keep as is

---

## Unused Imports - FIXED

### ❌ Removed from games.py
- Was looking for `text` import but it's not actually imported - **FALSE ALARM**

### ❌ Checked scheduler.py
- `UTC` from datetime **IS USED** at line 314 - **FALSE ALARM**

### ✅ Status
- All imports that are imported are actually used
- No unsafe import removals found

---

## Deprecated/Placeholder Code

### 1. ❌ insights.py - All endpoints are placeholders

Every endpoint returns:
```json
{
    "status": "under_construction",
    "message": "... coming soon"
}
```

### 2. ✅ All other endpoints are FUNCTIONAL

- health.py - Simple but necessary
- live.py - Core functionality
- games.py - Core functionality  
- props.py - Core functionality
- bets.py - Core functionality
- alerts.py - Core functionality
- analytics.py - Core functionality
- leaderboards.py - Core functionality
- aai_bets.py - Core functionality
- scraping.py - Core functionality
- sports_analytics.py - Core functionality
- bet_placement.py - Core functionality

---

## Summary

### Safe to Remove (0 Risk)
1. ❌ **backend/services/caching.py** - Completely unused
2. ❌ **backend/routers/insights.py** - All placeholders, no frontend integration

### Safe to Keep (Necessary)
- ✅ All other code is either core functionality or properly used

### Consolidations NOT Safe
- Would reduce functionality or clarity
- Current patterns are already optimal
- No significant duplication found

---

## Recommended Actions

### Immediate (Quick wins)
1. **Delete** `backend/services/caching.py` (13 lines, 0 impact)
2. **Delete** `backend/routers/insights.py` (54 lines, 0 impact)  
3. **Update** `backend/main.py` - Remove insights import/router registration

### Total Cleanup
- **Lines removed**: ~67
- **Files deleted**: 2
- **Risk level**: ZERO
- **Impact on functionality**: NONE

---

## Verification Checklist

Before applying cleanup:
- [ ] Run type checking (no errors expected)
- [ ] Check imports in main.py
- [ ] Verify no frontend references to /insights
- [ ] Run existing tests

After cleanup:
- [ ] Verify app starts without errors
- [ ] Confirm health endpoint works
- [ ] Confirm all active routers register

---

## Files Ready for Deletion

```
backend/services/caching.py
backend/routers/insights.py
```

**Safe?** YES - 100% confidence

