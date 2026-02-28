import pytest
import asyncio

# Example: Import the script to test
from backend.scripts.backfill_nhl_only import main as nhl_main

@pytest.mark.asyncio
def test_nhl_backfill_runs():
    # This test checks that the NHL backfill script runs without raising exceptions
    try:
        asyncio.run(nhl_main())
    except Exception as e:
        pytest.fail(f"NHL backfill script failed: {e}")

# Repeat for other scripts as needed
