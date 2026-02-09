import asyncio
from backend.services.espn_client import ESPNClient
from datetime import datetime, timedelta

async def test():
    client = ESPNClient()
    start = datetime.utcnow().strftime('%Y%m%d')
    end = (datetime.utcnow() + timedelta(days=1)).strftime('%Y%m%d')
    url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={start}-{end}&limit=1000'
    print(f"Fetching: {url}")
    
    import aiohttp
    session = aiohttp.ClientSession()
    try:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response length: {len(text)}")
            print(f"First 500 chars: {text[:500]}")
    finally:
        await session.close()

asyncio.run(test())
