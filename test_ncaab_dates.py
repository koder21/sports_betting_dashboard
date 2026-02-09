import asyncio
import aiohttp
from datetime import datetime, timedelta

async def test():
    # Try different date ranges
    for days_forward in [0, 1, 2, 3, 4, 5, 7]:
        for days_back in [0, 1, 2, 3]:
            start = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y%m%d')
            end = (datetime.utcnow() + timedelta(days=days_forward)).strftime('%Y%m%d')
            url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={start}-{end}&limit=1000'
            
            session = aiohttp.ClientSession()
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        events = data.get('events', [])
                        print(f"✓ {start}-{end}: {len(events)} games found")
                        if len(events) > 0:
                            for event in events[:5]:
                                comp = event.get('competitions', [{}])[0]
                                comps = comp.get('competitors', [])
                                home = comps[0].get('team', {}).get('displayName') if len(comps) > 0 else 'N/A'
                                away = comps[1].get('team', {}).get('displayName') if len(comps) > 1 else 'N/A'
                                print(f"    {home} vs {away}")
                        break
            except Exception as e:
                print(f"✗ {start}-{end}: {e}")
            finally:
                await session.close()

asyncio.run(test())
