import asyncio
import aiohttp
import json

async def test_ncaab():
    url = "https://cdn.espn.com/core/mens-college-basketball/scoreboard?xhr=1"
    
    print(f"Fetching NCAAB games from CDN...")
    session = aiohttp.ClientSession()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            text = await resp.text()
            # Try to parse as JSON
            try:
                data = json.loads(text)
                events = data.get("events", [])
                print(f"Found {len(events)} games")
                
                for event in events:
                    name = event.get("name", "")
                    if "UConn" in name or "St. John" in name:
                        print(f"\n✓ Found UConn/St. John's game:")
                        print(f"  Name: {name}")
                        print(f"  Date: {event.get('date')}")
                        print(f"  UID: {event.get('uid')}")
                        
                        comps = event.get("competitions", [])
                        if comps:
                            comp = comps[0]
                            comps_list = comp.get("competitors", [])
                            for comp_item in comps_list:
                                team = comp_item.get("team", {})
                                location = comp_item.get("homeAway", "unknown")
                                print(f"    {location}: {team.get('displayName')} (id: {team.get('id')})")
                            
                            status = comp.get("status", {}).get("type", {}).get("name", "Unknown")
                            print(f"  Status: {status}")
            except json.JSONDecodeError:
                print("Response is not JSON, trying to extract from text...")
                idx = text.find("UConn")
                if idx >= 0:
                    print(text[max(0, idx-500):idx+1000])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

asyncio.run(test_ncaab())
