import asyncio

from backend.scheduler.tasks import Scheduler
from backend.db import get_session
from backend.scheduler.write_queue import DatabaseWriteQueue

async def main():
    scheduler = Scheduler(get_session)
    # Start the write queue worker
    await scheduler.write_queue.start_worker()
    # Enqueue the backfill operation (uses queue, async context)
    scheduler.write_queue.enqueue(
        "manual_backfill_player_stats",
        scheduler._execute_backfill_player_stats
    )
    # Wait for queue to empty and stop worker
    await scheduler.write_queue.wait_empty(timeout=60.0)
    await scheduler.write_queue.stop_worker()

if __name__ == "__main__":
    asyncio.run(main())
