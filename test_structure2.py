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
            
            # Check content
            if "content" in data:
                content = data["content"]
                print(f"content type: {type(content)}")
                if isinstance(content, dict):
                    print(f"content keys: {list(content.keys())[:15]}")
                    if "scoreboard" in content:
                        sb = content["scoreboard"]
                        print(f"scoreboard found: {type(sb)}")
                        if isinstance(sb, dict):
                            print(f"scoreboard keys: {list(sb.keys())}")
                            if "leagues" in sb:
                                leagues = sb["leagues"]
                                if leagues:
                                    print(f"\n✓ Found {len(leagues)} league(s)")
                                    for league in leagues:
                                        if "events" in league:
                                            events = league["events"]
                                            print(f"  League has {len(events)} events")
                                            for e in events[:3]:
                                                print(f"    - {e.get('name', 'N/A')}")
    finally:
        await session.close()

asyncio.run(test())
