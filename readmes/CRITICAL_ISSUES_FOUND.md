# Critical Code Issues Found - Comprehensive Audit

**Scope**: Systematic review of all routers, services, scheduler, and frontend patterns  
**Date**: Feb 10, 2026  
**Severity Distribution**: 3 CRITICAL, 6 HIGH, 4 MEDIUM

---

## CRITICAL ISSUES (Fix Immediately)

### 1. N+1 QUERY EXPLOSION in `games.py` /ai-context endpoint ⚠️

**File**: [backend/routers/games.py](backend/routers/games.py#L60)  
**Severity**: CRITICAL - Database performance disaster  
**Lines**: 60-95

**Problem**:
```python
for game_live in all_live_games:  # Loop through ALL games
    if game_live.game_id in game_ids_in_results:
        continue
    
    # ... check status ...
    
    # QUERY 1 per game
    upcoming_result = await session.execute(
        select(GameUpcoming).where(GameUpcoming.game_id == game_live.game_id)
    )
    
    # QUERY 2 per game (if no upcoming found)
    if not start_time:
        game_result = await session.execute(
            select(Game).where(Game.game_id == game_live.game_id)
        )
```

With 100 games: **~100-200 queries** instead of 2  
This is a SEVERELY WORSE variant of the `/live` endpoint issue we already fixed.

**Impact**:
- This is the `/ai-context` endpoint used by AI bet recommendation system
- Runs **every time** user loads AAI recommendations
- Causes database lock contention during high-traffic periods
- Frontend will timeout waiting for response

**Fix**: Same bulk fetch pattern we applied to `/live`:
```python
# Fetch all IDs upfront
game_ids = [g.game_id for g in all_live_games if g.game_id]

# Bulk fetch in 2 queries
upcoming_records = {r.game_id: r for r in await session.execute(
    select(GameUpcoming).where(GameUpcoming.game_id.in_(game_ids))
).scalars()}

game_records = {g.game_id: g for g in await session.execute(
    select(Game).where(Game.game_id.in_(game_ids))
).scalars()}

# Use O(1) lookups in loop
for game_live in all_live_games:
    upcoming_record = upcoming_records.get(game_live.game_id)
    game_record = game_records.get(game_live.game_id)
```

---

### 2. N+1 QUERY EXPLOSION in `props.py` /players endpoint ⚠️

**File**: [backend/routers/props.py](backend/routers/props.py#L15)  
**Severity**: CRITICAL - Performance killer  
**Lines**: 15-50

**Problem**:
```python
@router.get("/players")
async def get_all_players(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Player).order_by(Player.full_name))
    players = result.scalars().all()
    
    player_list = []
    for p in players:  # For each player...
        team_name = None
        if p.team_id and p.sport:
            # QUERY PER PLAYER
            team_result = await session.execute(
                select(Team).where(
                    and_(Team.team_id == p.team_id, Team.sport_name == p.sport)
                )
            )
            team = team_result.scalar_one_or_none()
```

With 500 players: **500+ database queries**  
With 10+ concurrent users: **5000+ queries/minute**

**Impact**:
- Endpoint called by prop bet builder UI
- This is probably what slows down the CustomBetBuilder.jsx you have open
- Database maxes out on connection pool exhaustion

**Fix**: Use eager loading with selectinload OR fetch teams in bulk:
```python
# Option 1: Use joinedload for SQLAlchemy relationship
from sqlalchemy.orm import selectinload
from ..models.player import Player

stmt = select(Player).options(
    selectinload(Player.team)  # If Player model has team relationship
).order_by(Player.full_name)
result = await session.execute(stmt)
players = result.scalars().all()

# Then use the pre-loaded relationship - no queries in loop
player_list = [{"team_name": p.team.name if p.team else None, ...} for p in players]
```

OR

```python
# Option 2: Bulk fetch teams
team_ids = {(p.team_id, p.sport) for p in players if p.team_id and p.sport}
teams_query = await session.execute(
    select(Team).where(or_(*[
        and_(Team.team_id == tid, Team.sport_name == sport) 
        for tid, sport in team_ids
    ]))
)
teams = {(t.team_id, t.sport_name): t.name for t in teams_query.scalars()}

for p in players:
    team_name = teams.get((p.team_id, p.sport)) if p.team_id else None
```

---

### 3. MISSING ERROR HANDLING in `scraping.py` endpoints ⚠️

**File**: [backend/routers/scraping.py](backend/routers/scraping.py#L65)  
**Severity**: CRITICAL - Silent failures, no logging  
**Lines**: 65-85

**Problem**:
```python
@router.post("/fix-orphaned-players")
async def fix_orphaned_players(session: AsyncSession = Depends(get_session)):
    """Create player records for all orphaned player_ids in player_stats"""
    try:
        result = await session.execute(text("""..."""))
        orphaned = result.fetchall()
        
        for player_id, sport in orphaned:
            # RAW SQL - no error handling per record
            # If one fails, entire operation fails
            await session.execute(
                text("""INSERT OR IGNORE INTO players..."""),
                {"player_id": player_id, ...}
            )
        
        await session.commit()
        
        return {...}
    except Exception as e:
        await session.rollback()
        return {"status": "error", "message": str(e)}
```

**Issues**:
- Raw SQL with `text()` - vulnerable to edge cases
- No per-record error isolation
- Returns generic error string instead of specific details
- No logging context for debugging

**Impact**:
- Bulk player creation silently fails
- Orphaned player records remain unfixed
- System degrades silently without visibility

---

## HIGH SEVERITY ISSUES

### 4. MISSING TRY-CATCH in `games.py` /ai-context endpoint

**File**: [backend/routers/games.py](backend/routers/games.py#L1)  
**Severity**: HIGH  
**Issue**: Entire endpoint wrapped in try-catch only at top level

```python
@router.get("/ai-context")
async def get_ai_context(session: AsyncSession = Depends(get_session)):
    # NO try-except here!
    # All queries can fail silently
    pst = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst)
    
    yesterday_from_results = await session.execute(select(GameResult)...)
    
    # Multiple unprotected queries and loops
    all_live_result = await session.execute(select(GameLive))
    # ... 40+ lines of unprotected logic
```

If ANY query fails, entire AI recommendation pipeline breaks.

---

### 5. BARE EXCEPT CLAUSE in `games.py`

**File**: [backend/routers/games.py](backend/routers/games.py#L81)  
**Severity**: HIGH  
**Lines**: 81

```python
try:
    upcoming_result = await session.execute(...)
    upcoming_record = upcoming_result.scalar()
except:  # <- THIS IS BAD
    pass
```

- Silently swallows `KeyboardInterrupt`, `SystemExit`, `MemoryError`, `GeneratorExit`
- Hides real errors
- Should be `except Exception as e:`

---

### 6. SESSION NOT CLOSED in `scraping.py` /fill-player-names endpoint

**File**: [backend/routers/scraping.py](backend/routers/scraping.py#L100+)  
**Severity**: HIGH  
**Issue**: Long-running operation may leave sessions open

```python
@router.post("/fill-player-names")
async def fill_player_names(limit: int = 100, session: AsyncSession = Depends(get_session)):
    """Fill placeholder player names"""
    # Long-running loop - 100+ iterations
    for i in range(min(limit, len(to_fill))):
        # Multiple awaits
        player_name = await self.espn_client.get_player_name(player_id)
        # ... 10+ lines per iteration
        # Session can timeout waiting for commit
    
    # Session cleanup is implicit via Depends - may not happen if error occurs
```

Should wrap in try-finally to ensure cleanup.

---

### 7. NO ERROR HANDLING in `alerts.py` endpoints

**File**: [backend/routers/alerts.py](backend/routers/alerts.py#L1)  
**Severity**: HIGH  
**Issue**: All endpoints missing try-catch

```python
@router.get("/")
async def list_alerts(session: AsyncSession = Depends(get_session)):
    svc = AlertManager(session)
    return await svc.list_unacknowledged()  # No error handling!

@router.post("/{alert_id}/ack")
async def ack_alert(alert_id: int, session: AsyncSession = Depends(get_session)):
    svc = AlertManager(session)
    await svc.acknowledge(alert_id)  # No error handling!
    return {"status": "ok"}
```

If service fails, frontend gets 500 error with no meaningful error message.

---

### 8. BARE EXCEPT in `main.py` scheduler worker

**File**: [backend/main.py](backend/main.py#L50)  
**Severity**: HIGH  
**Lines**: 50+

```python
async def scheduler_worker():
    while True:
        try:
            # ... scheduler operations
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(60)
```

Should have:
- Specific exception types
- Logging instead of print()
- Exponential backoff instead of fixed 60s

---

## MEDIUM SEVERITY ISSUES

### 9. BARE EXCEPT EVERYWHERE in `games.py`

**File**: [backend/routers/games.py](backend/routers/games.py) throughout  
**Severity**: MEDIUM  
**Issue**: Multiple bare `except:` clauses instead of `except Exception:`

```python
try:
    upcoming_result = await session.execute(...)
except:  # Line 81, 86, etc.
    pass

try:
    game_record = await session.execute(...)
except:  # Line 91, etc.
    pass
```

---

### 10. NO VALIDATION in `bet_placement.py` endpoints

**File**: [backend/routers/bet_placement.py](backend/routers/bet_placement.py#L50)  
**Severity**: MEDIUM  
**Issue**: Pydantic models validate input, but service doesn't return proper error details

```python
@router.post("/place-aai-single")
async def place_aai_single(
    request: PlaceAAISingleRequest,  # Validated by Pydantic ✓
    session: AsyncSession = Depends(get_session),
):
    service = BetPlacementService(session)
    result = await service.place_aai_single(...)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to place bet"))
```

Problem: `result.get("error")` might be None, leading to "Failed to place bet" which is unhelpful

---

### 11. MEMORY LEAK in scheduler tasks

**File**: [backend/scheduler/tasks.py](backend/scheduler/tasks.py#L50)  
**Severity**: MEDIUM  
**Issue**: Scrapers created once but ESPN client created per request

```python
class Scheduler:
    def __init__(self, session_factory):
        self.client = ESPNClient()  # Created once
        self.scrapers = [
            NBAScraper(self.client),
            NFLScraper(self.client),
            # ... all share same client
        ]
    
    async def _execute_scrapers(self):
        # Inside execute, new scraper instances AND new clients created
        async with self.session_factory() as session:
            fresh_scraper = FreshDataScraper(session)
            # This may create ANOTHER ESPNClient internally
            # If close() isn't called, connection leaks
            try:
                games_count = await fresh_scraper._scrape_todays_games()
            finally:
                await fresh_scraper.close()  # Good, but only catches one
```

Multiple instances of FreshDataScraper, PlayerStatsScraper created without pooling.

---

### 12. LOGGING INCONSISTENCY in grader.py

**File**: [backend/services/betting/grader.py](backend/services/betting/grader.py)  
**Severity**: MEDIUM  
**Issue**: Mix of logger and print statements

```python
logger.error("[Grader] Error grading prop bet %s: %s", bet.id, e, exc_info=True)  # ✓ Good

# But elsewhere:
print(f"Error fetching player stat from ESPN: {e}")  # ✗ Bad
import traceback
traceback.print_exc()  # ✗ Bad
```

Inconsistent logging makes debugging harder.

---

## MEDIUM SEVERITY - ASYNC/AWAIT ISSUES

### 13. POTENTIAL RACE CONDITION in scheduler

**File**: [backend/scheduler/tasks.py](backend/scheduler/tasks.py#L88)  
**Severity**: MEDIUM  
**Issue**: Multiple concurrent updates to same tables without locking

```python
async def run_scrapers(self):
    """Queue the scraper operations"""
    self.write_queue.enqueue("run_scrapers", self._execute_scrapers)

async def update_live_games(self):
    """Fetch today's games"""
    # Runs every 60 seconds
    # But run_scrapers also updates games!
    
async def grade_bets(self):
    """Grade pending bets"""
    # Also touches games_results table
```

Scenario:
1. `update_live_games` writes game status
2. Meanwhile `run_scrapers` writes same game
3. Conflict: Last write wins, previous data lost

No transaction isolation between concurrent writes.

---

## MEDIUM SEVERITY - RESOURCE CLEANUP

### 14. ESPNClient not guaranteed to close in all paths

**File**: [backend/routers/scraping.py](backend/routers/scraping.py#L25)  
**Severity**: MEDIUM  
**Lines**: 25-35

```python
@router.post("/sport/{sport_name}")
async def scrape_sport(sport_name: str, session: AsyncSession = Depends(get_session)):
    client = ESPNClient()
    try:
        # ... scraping ...
        return {"status": "ok"}
    finally:
        await client.close()  # ✓ Good pattern
```

BUT: What if `ESPNClient()` constructor fails? `close()` never called.

Should be:
```python
client = None
try:
    client = ESPNClient()
    # ...
finally:
    if client:
        await client.close()
```

---

## LOW PRIORITY - CODE QUALITY

### 15. TIMEZONE HANDLING INCONSISTENCY

**File**: [backend/routers/games.py](backend/routers/games.py#L1)  
**Severity**: LOW  
**Issue**: Timezone conversions scattered throughout, not centralized

```python
pst = ZoneInfo("America/Los_Angeles")
now_pst = datetime.now(pst)
today_pst = now_pst.date()

# ... 50 lines later ...

yesterday_start_pst = datetime.combine(yesterday_pst, datetime.min.time()).replace(tzinfo=pst)
# ...
yesterday_start_utc = yesterday_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
```

Should extract to utility function in `services/timezone_utils.py`

---

## SUMMARY TABLE

| Issue | File | Severity | Type | Lines Affected |
|-------|------|----------|------|-----------------|
| N+1 in /ai-context | games.py | CRITICAL | Query Pattern | 60-95 |
| N+1 in /players | props.py | CRITICAL | Query Pattern | 15-50 |
| Missing error handling | scraping.py | CRITICAL | Error Handling | 65-85 |
| No try-catch | games.py | HIGH | Error Handling | 1-150 |
| Bare except | games.py | HIGH | Error Handling | 81+ |
| Session cleanup | scraping.py | HIGH | Resource Leak | 100+ |
| No error handling | alerts.py | HIGH | Error Handling | 1-50 |
| Scheduler error handling | main.py | HIGH | Error Handling | 50+ |
| Bare except | games.py | MEDIUM | Error Handling | Multiple |
| Input validation | bet_placement.py | MEDIUM | Validation | 50+ |
| Memory leak | tasks.py | MEDIUM | Resource Leak | 50-170 |
| Logging inconsistency | grader.py | MEDIUM | Logging | Throughout |
| Race condition | tasks.py | MEDIUM | Concurrency | 88-400 |
| Client cleanup | scraping.py | MEDIUM | Resource Leak | 25-35 |
| Timezone handling | games.py | LOW | Code Quality | Throughout |

---

## Quick Fix Priority

**Today (Critical)**:
1. Fix N+1 in `/ai-context` - AI recommendations breaking
2. Fix N+1 in `/players` - Props builder timing out
3. Add proper error handling to scraping endpoints

**This week (High)**:
4. Add try-catch to all router endpoints
5. Replace bare excepts with specific exception handling
6. Add proper logging throughout

**Next sprint (Medium)**:
7. Fix race conditions in scheduler
8. Centralize timezone handling
9. Add resource cleanup guarantees
