# Testing Guide: Circuit Breaker, Metrics, and Monitoring

## What Was Added

### 1. Circuit Breaker Pattern (`backend/services/circuit_breaker.py`)
Prevents cascading failures when ESPN APIs go down.

**States:**
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures detected, requests rejected with exception
- **HALF_OPEN**: Testing if service recovered after timeout

**Configuration:**
- `failure_threshold`: 5 failures before opening
- `recovery_timeout`: 60 seconds before attempting recovery

### 2. Metrics Logging (`backend/services/metrics.py`)
Tracks performance of all scraping operations.

**Metrics Collected:**
- Operation name and duration
- Success/failure status
- Error type and message
- Timestamp
- Custom metadata

**Operations Currently Instrumented:**
- `fresh_scrape_games`
- `fresh_scrape_injuries`
- `fresh_scrape_weather`
- `scheduler_execute_scrapers`
- `scheduler_update_live_games`
- `scheduler_update_game_statuses`

### 3. New Metrics Endpoint
`GET /games/metrics/scraper-performance`

Returns current performance summary and recent events.

---

## How to Test

### Test 1: Verify Metrics Collection
**Objective:** Confirm metrics are being recorded

**Steps:**
1. Start the backend:
   ```bash
   cd /Users/dakotanicol/sports_betting_dashboard
   source .venv/bin/activate
   python -m backend.main
   ```

2. Trigger a fresh scrape by clicking "Copy for AI" button in frontend

3. Query metrics endpoint:
   ```bash
   curl http://localhost:8000/games/metrics/scraper-performance
   ```

4. **Expected Output:**
   ```json
   {
     "summary": {
       "fresh_scrape_games": {
         "count": 1,
         "success": 1,
         "failed": 0,
         "total_duration": 3.45,
         "avg_duration": 3.45,
         "min_duration": 3.45,
         "max_duration": 3.45,
         "success_rate": "100.0%"
       },
       "fresh_scrape_injuries": {
         "count": 1,
         "success": 1,
         "failed": 0,
         ...
       },
       ...
     },
     "total_events": 3,
     "last_10_events": [
       {
         "operation": "fresh_scrape_games",
         "duration": "3.45s",
         "success": true,
         "error_type": null,
         "timestamp": "2026-02-11T10:30:45.123456"
       },
       ...
     ]
   }
   ```

5. **Verify:**
   - ✅ All operations have success_rate = "100.0%"
   - ✅ Durations are reasonable (games ~3-5s, injuries ~30-60s, weather ~5-10s)
   - ✅ Recent events show successful completions

---

### Test 2: Performance Comparison
**Objective:** Confirm optimizations are working

**Steps:**
1. Call metrics endpoint before and after a scheduler cycle:
   ```bash
   # Before (initial call)
   curl http://localhost:8000/games/metrics/scraper-performance > before.json
   
   # Wait for scheduler to run (2 hour cycle) or manually trigger
   # python check_all_live_yesterday.py
   
   # After
   curl http://localhost:8000/games/metrics/scraper-performance > after.json
   ```

2. **Compare durations:**
   - Games scrape: Should be < 5 seconds
   - Injuries scrape: Should be < 60 seconds (was 5+ minutes)
   - Weather scrape: Should be < 10 seconds
   - Scheduler cycle: Should be < 2-3 minutes total

3. **Check success rates:**
   - All operations should have 100% success rate
   - If any operation has failures, review error_type in metrics

---

### Test 3: Error Handling
**Objective:** Verify graceful error handling

**Steps:**
1. Temporarily disconnect internet or block ESPN API:
   ```bash
   # Mac: Use Network Link Conditioner or block in firewall
   sudo pfctl -f /etc/pf.conf  # Requires setup
   ```

2. Trigger a fresh scrape

3. Check metrics endpoint:
   ```bash
   curl http://localhost:8000/games/metrics/scraper-performance
   ```

4. **Expected Behavior:**
   - Operations may have `failed: 1, success: 0`
   - `success_rate` will show partial failures
   - `error_type` will indicate connection error
   - System continues running (resilient)

5. **Restore connection and verify recovery:**
   - Next scrape should succeed
   - Metrics will show successful attempts

---

### Test 4: Circuit Breaker Activation
**Objective:** Verify circuit breaker prevents repeated failures

**Steps:**
1. Circuit breaker is available in code but not yet integrated into ESPNClient

2. To test circuit breaker behavior manually:
   ```python
   # In Python shell
   from backend.services.circuit_breaker import circuit_breaker_manager
   
   # Simulate failures
   breaker = circuit_breaker_manager.get_breaker("test_api")
   print(breaker.get_status())  # Should show CLOSED
   
   # Get all statuses
   print(circuit_breaker_manager.get_all_status())
   ```

3. Circuit breaker will prevent thundering herd if ESPN goes down

---

### Test 5: Long-Running Operations
**Objective:** Verify system doesn't timeout on long operations

**Steps:**
1. Click "Copy for AI" and wait for injury scrape to complete
   - Monitor logs for progress
   - Should complete in 30-60 seconds (not timeout)

2. Check metrics for operation duration:
   ```bash
   curl http://localhost:8000/games/metrics/scraper-performance | grep fresh_scrape_injuries
   ```

3. **Expected:**
   - `"duration": "30.45s"` to `"45.60s"` (NOT timing out)
   - `"success": true`

---

## Monitoring Recommendations

### Daily Checks
1. Monitor success rates in metrics endpoint
2. Watch for repeated error_type patterns
3. Check average durations for regression

### Weekly Checks
1. Review scheduler performance summary
2. Look for patterns in failures
3. Consider optimizations if durations increase

### Alerting (Future Enhancement)
Consider adding alerts for:
- Success rate < 90%
- Any operation > 5 minutes
- Circuit breaker OPEN state

---

## Logging

All metrics are logged with proper structure. Check logs with:

```bash
# View recent logs
tail -100 backend/logs/app.log | grep "SCRAPER\|metric\|✓\|✗"

# View specific operation
tail -100 backend/logs/app.log | grep "fresh_scrape_injuries"

# Count successes/failures
tail -1000 backend/logs/app.log | grep "✓\|✗" | sort | uniq -c
```

---

## Integration Points

### Where Metrics Are Collected
1. **Fresh Data Scraper** (`backend/services/aai/fresh_data_scraper.py`)
   - Individual measurements for games, injuries, weather

2. **Scheduler Tasks** (`backend/scheduler/tasks.py`)
   - Full scheduler cycle measurements
   - Individual task measurements

3. **Metrics Endpoint** (`backend/routers/games.py`)
   - Returns real-time performance data

### Where Circuit Breaker Can Be Added
1. **ESPNClient** (`backend/services/espn_client.py`)
   - Wrap API calls to detect consecutive failures
   - Example: 5 failed requests to ESPN → Open circuit, stop making requests

2. **Sport-Specific Scrapers**
   - Individual circuit breakers per sport (NBA, NFL, NHL, etc.)
   - Prevent one broken sport from blocking others

---

## Semaphore Decision

**Decision:** NO semaphore added

**Reasoning:**
- Current concurrent request volume (20-50) is reasonable
- ESPN doesn't appear to have rate limiting issues
- Per-request timeout (10s) prevents hanging
- Circuit breaker handles ESPN failures better than semaphore
- Can be added later with minimal code changes if needed

**If rate limiting becomes an issue:**
```python
# Add to ESPNClient
self.semaphore = asyncio.Semaphore(20)  # Max 20 concurrent

async def get_json(self, url):
    async with self.semaphore:
        return await self._get_json_impl(url)
```

---

## Success Criteria

✅ **All tests pass when:**
1. Metrics endpoint returns all operations with 100% success rate
2. Operation durations match optimization targets (30-60s for injuries, <5s for games)
3. Error handling shows graceful degradation (partial failures still save data)
4. System continues running even if ESPN APIs are down
5. Circuit breaker code is available for future use

✅ **System is production-ready when:**
- Metrics consistently show high success rates (>95%)
- No repeated error patterns
- All operations complete within SLA (< 2-3 min scheduler cycle)
- Monitoring endpoint is accessible for health checks
