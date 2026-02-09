import asyncio
import aiohttp
import json

async def test():
    url = "https://cdn.espn.com/core/mens-college-basketball/scoreboard?xhr=1"
    session = aiohttp.ClientSession()
    try:
        async with session.get(url) as resp:
            text = await resp.text()
            data = json.loads(text)
            
            sbData = data.get("content", {}).get("sbData", {})
            events = sbData.get("events", [])
            print(f"Events: {len(events)}")
            
            for e in events:
                name = e.get("name", "")
                date = e.get("date", "")
                if "UConn" in name or "St. John" in name:
                    print(f"\n✓✓✓ FOUND IT!")
                    print(f"Name: {name}")
                    print(f"Date: {date}")
                    print(f"ID: {e.get('id')}")
                    comps = e.get("competitions", [])
                    if comps:
                        comp = comps[0]
                        for c in comp.get("competitors", []):
                            team = c.get("team", {})
                            ha = c.get("homeAway")
                            score = c.get("score")
                            print(f"  {ha}: {team.get('displayName')} (score: {score})")
                        status = comp.get("status", {}).get("type", {}).get("name")
                        print(f"  Status: {status}")
    finally:
        await session.close()

asyncio.run(test())
