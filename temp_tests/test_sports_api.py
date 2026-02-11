#!/usr/bin/env python3
"""Test ESPN API endpoints for all configured sports"""
import asyncio
from backend.services.espn_client import ESPNClient

async def test_sports():
    client = ESPNClient()
    sports_tests = [
        ('basketball', 'nba', 'NBA'),
        ('basketball', 'mens-college-basketball', 'NCAAB'),
        ('football', 'nfl', 'NFL'),
        ('football', 'college-football', 'NCAAF'),
        ('hockey', 'nhl', 'NHL'),
        ('mma', 'ufc', 'UFC'),
        ('soccer', 'eng.1', 'EPL'),
    ]
    
    print('Testing ESPN API endpoints for all sports:')
    print('=' * 60)
    
    for sport_type, league, name in sports_tests:
        url = f'https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard'
        try:
            data = await client.get_json(url)
            if data and 'events' in data:
                print(f'✓ {name:8} ({sport_type}/{league}): {len(data["events"])} games found')
            else:
                print(f'⚠ {name:8} ({sport_type}/{league}): No events in response')
        except Exception as e:
            print(f'✗ {name:8} ({sport_type}/{league}): Error - {e}')
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_sports())
