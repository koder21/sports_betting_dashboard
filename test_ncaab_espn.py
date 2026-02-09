import asyncio
from backend.services.espn_client import ESPNClient
from datetime import datetime, timedelta

async def test():
    client = ESPNClient()
    start = datetime.utcnow().strftime('%Y%m%d')
    end = (datetime.utcnow() + timedelta(days=1)).strftime('%Y%m%d')
    url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={start}-{end}&limit=1000'
    print(f"Fetching: {url}")
    data = await client.get_json(url)
    if data:
        events = data.get('events', [])
        print(f'Found {len(events)} games')
        for event in events[:15]:
            comp = event.get('competitions', [{}])[0]
            comps = comp.get('competitors', [])
            home = comps[0].get('team', {}).get('displayName') if len(comps) > 0 else 'N/A'
            away = comps[1].get('team', {}).get('displayName') if len(comps) > 1 else 'N/A'
            status = event.get('status', {}).get('type', {}).get('name', 'Unknown')
            print(f"{home} vs {away} ({status})")
            if 'UConn' in home or 'UConn' in away or 'St. John' in home or 'St. John' in away:
                print(f"  ^^^ THIS IS THE GAME! Event ID: {event.get('id')}")
    else:
        print("No data returned")
    await client.close()

asyncio.run(test())
