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
            print(f"sbData keys: {list(sbData.keys())}")
            
            if "leagues" in sbData:
                leagues = sbData["leagues"]
                print(f"\n✓ Found {len(leagues)} league(s)")
                for league in leagues:
                    if "events" in league:
                        events = league["events"]
                        print(f"  League has {len(events)} events")
                        for e in events:
                            name = e.get("name", "N/A")
                            if "UConn" in name or "St. John" in name:
                                print(f"\n✓✓✓ FOUND THE GAME!")
                                print(f"    Name: {name}")
                                print(f"    Date: {e.get('date')}")
                                print(f"    ID: {e.get('id')}")
                                
                                comps = e.get("competitions", [])
                                if comps:
                                    comp = comps[0]
                                    for competitor in comp.get("competitors", []):
                                        team = competitor.get("team", {})
                                        ha = competitor.get("homeAway", "")
                                        print(f"    {ha}: {team.get('displayName')}")
                                    print(f"    Status: {comp.get('status', {}).get('type', {}).get('name')}")
                            else:
                                print(f"  - {name}")
    finally:
        await session.close()

asyncio.run(test())
