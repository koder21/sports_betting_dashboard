import asyncio
import aiohttp

async def test():
    url = 'https://site.api.espn.com/apis/site/v2/sports'
    
    print(f"Querying sports: {url}")
    session = aiohttp.ClientSession()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                sports = data.get('sports', [])
                print(f"Available sports ({len(sports)}):")
                for sport in sports:
                    name = sport.get('name')
                    leagues = sport.get('leagues', [])
                    print(f"  {name}: {len(leagues)} leagues")
                    for league in leagues:
                        print(f"    - {league.get('name')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

asyncio.run(test())
