import pytest
import asyncio

# Example: Integration test for backfill scripts
from backend.scripts.backfill_nhl_only import main as nhl_main
from backend.scripts.backfill_nba_only import main as nba_main

@pytest.mark.asyncio
def test_backfill_scripts_integration():
    # Run NHL and NBA backfill scripts sequentially to check integration
    try:
        asyncio.run(nhl_main())
        asyncio.run(nba_main())
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")

# Extend with more scripts as needed
