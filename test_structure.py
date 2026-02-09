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
            
            print("Top-level keys:", list(data.keys())[:20])
            
            if "leagues" in data:
                leagues = data["leagues"]
                if leagues:
                    print(f"\nLeagues: {len(leagues)}")
                    print(f"League 0 keys: {list(leagues[0].keys())}")
                    if "events" in leagues[0]:
                        events = leagues[0]["events"]
                        print(f"Events in league 0: {len(events)}")
                        
                        for event in events[:5]:
                            name = event.get("name", "")
                            print(f"  - {name}")
                            
                            if "UConn" in name or "St. John" in name:
                                print(f"    ✓✓✓ FOUND! Full event:")
                                print(json.dumps(event, indent=2)[:1000])
    finally:
        await session.close()

asyncio.run(test())
