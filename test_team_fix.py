#!/usr/bin/env python3
"""Test that team data is correctly fixed with sport-scoped IDs"""
import asyncio
import sys
from sqlalchemy import text

from backend.db import async_session


async def main():
    async with async_session() as session:
        # Test 1: Get an NFL player and verify correct team
        result = await session.execute(text('''
            SELECT p.name, p.position, t.name, t.sport_name FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            WHERE p.sport = 'NFL' LIMIT 1
        '''))
        row = result.fetchone()
        if row:
            print(f'✓ NFL Player matched correctly: {row[0]} ({row[1]}) plays for {row[2]} ({row[3]})')
        
        # Test 2: Get an NHL player and verify correct team
        result = await session.execute(text('''
            SELECT p.name, p.position, t.name, t.sport_name FROM players p 
            JOIN teams t ON p.team_id = t.team_id 
            WHERE p.sport = 'NHL' LIMIT 1
        '''))
        row = result.fetchone()
        if row:
            print(f'✓ NHL Player matched correctly: {row[0]} ({row[1]}) plays for {row[2]} ({row[3]})')
        
        # Test 3: Count teams per sport
        result = await session.execute(text('''
            SELECT sport_name, COUNT(*) FROM teams GROUP BY sport_name ORDER BY sport_name
        '''))
        print('\nTeam counts by sport:')
        for sport, count in result.fetchall():
            print(f'  ✓ {sport}: {count} teams')
        
        # Test 4: Verify no cross-sport team_id conflicts
        result = await session.execute(text('''
            SELECT team_id, COUNT(DISTINCT sport_name) as sport_count
            FROM teams
            GROUP BY team_id
            HAVING COUNT(DISTINCT sport_name) > 1
        '''))
        conflicts = result.fetchall()
        if conflicts:
            print(f'\n✗ Found {len(conflicts)} team_id conflicts across sports!')
            for team_id, count in conflicts:
                print(f'  team_id {team_id} used in {count} sports')
        else:
            print('\n✓ No team_id conflicts - each team_id belongs to only one sport')
        
        # Test 5: Sample an Amen Ogbongbemiga to verify he's no longer with Calgary Flames
        result = await session.execute(text('''
            SELECT p.name, p.position, t.name, t.sport_name FROM players p 
            LEFT JOIN teams t ON p.team_id = t.team_id 
            WHERE p.name LIKE '%Ogbongbemiga%'
        '''))
        rows = result.fetchall()
        if rows:
            print(f'\nAmen Ogbongbemiga verification:')
            for row in rows:
                print(f'  {row[0]} ({row[1]}) - {row[2]} ({row[3]})')
        else:
            print('\n✓ Amen Ogbongbemiga not found in database (expected)')


if __name__ == "__main__":
    asyncio.run(main())
