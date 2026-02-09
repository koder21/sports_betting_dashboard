import asyncio
import sys, os
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.espn_client import ESPNClient, BASE_SITE
from backend.db import AsyncSessionLocal
from backend.repositories.team_repo import TeamRepository
from sqlalchemy import text

async def main():
    client = ESPNClient()
    url = f"{BASE_SITE}/basketball/nba/teams"
    print('Fetching:', url)
    data = await client.get_json(url)
    if not data:
        print('no data')
        return
    teams_list = data.get('sports', [])[0].get('leagues', [])[0].get('teams', [])
    print('teams_list len', len(teams_list))
    async with AsyncSessionLocal() as session:
        res = await session.execute(text('SELECT COUNT(*) FROM teams'))
        print('before teams:', res.scalar_one())
        repo = TeamRepository(session)
        for item in teams_list[:5]:
            team_data = item.get('team', {})
            espn_id = team_data.get('id')
            name = team_data.get('displayName')
            print('upserting', espn_id, name)
            await repo.upsert(espn_id=str(espn_id), name=name, sport_id=1, record='', stats_json={})
        await session.commit()
        res = await session.execute(text('SELECT COUNT(*) FROM teams'))
        print('after teams:', res.scalar_one())
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
