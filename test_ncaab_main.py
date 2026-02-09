import asyncio
import aiohttp
from datetime import datetime, timedelta

async def test():
    # Try the articles endpoint which sometimes shows current games/results
    url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'
    
    print(f"Trying main endpoint: {url}")
    session = aiohttp.ClientSession()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Available keys: {list(data.keys())}")
                # Look for games or articles
                if 'articles' in data:
                    articles = data['articles'][:3]
                    for article in articles:
                        print(f"  - {article.get('headline')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

asyncio.run(test())
