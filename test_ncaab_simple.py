import asyncio
import aiohttp
from datetime import datetime, timedelta

async def test():
    # Try a few specific date ranges
    test_ranges = [
        (0, 0),   # today only
        (0, 1),   # today + tomorrow
        (1, 0),   # yesterday only
        (1, 1),   # yesterday + today
        (2, 2),   # 2 days back, 2 forward
        (0, 7),   # today + 7 days forward
    ]
    
    for days_back, days_forward in test_ranges:
        start = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y%m%d')
        end = (datetime.utcnow() + timedelta(days=days_forward)).strftime('%Y%m%d')
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={start}-{end}&limit=100'
        
        print(f"Trying {start}-{end}...", end=" ", flush=True)
        session = aiohttp.ClientSession()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    events = data.get('events', [])
                    print(f"✓ {len(events)} games")
                else:
                    print(f"✗ Status {resp.status}")
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
        finally:
            await session.close()

asyncio.run(test())
