#!/bin/bash
# Monitor scraper progress by checking database stats

cd /Users/dakotanicol/sports_betting_dashboard

echo "=== Scraper Status (PID 1909) ==="
ps -p 1909 -o pid,%cpu,%mem,etime,state 2>/dev/null || echo "Scraper not running"

echo ""
echo "=== Database Stats Count ==="
/Users/dakotanicol/sports_betting_dashboard/venv/bin/python -c "
import asyncio
from backend.db import AsyncSessionLocal
from sqlalchemy import select, func
from backend.models.player_stats import PlayerStats

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlayerStats.sport, func.count(PlayerStats.id))
            .group_by(PlayerStats.sport)
            .order_by(PlayerStats.sport)
        )
        total = 0
        for sport, count in result.all():
            print(f'  {sport}: {count:,} records')
            total += count
        print(f'  ---')
        print(f'  TOTAL: {total:,} records')

asyncio.run(main())
"
