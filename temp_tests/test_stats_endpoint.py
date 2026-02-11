#!/usr/bin/env python3
"""Test the game details endpoint"""
import asyncio
import httpx
import json

async def test_endpoint():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get('http://localhost:8000/api/games/401810626/detailed')
            data = response.json()
            
            print("=== ENDPOINT RESPONSE TEST ===\n")
            print(f"Status Code: {response.status_code}")
            print(f"Game ID: {data.get('game', {}).get('game_id')}")
            print(f"Game Status: {data.get('game', {}).get('status')}")
            print(f"Home Team: {data.get('game', {}).get('home', {}).get('team_name')}")
            print(f"Away Team: {data.get('game', {}).get('away', {}).get('team_name')}")
            print(f"\nHome Team Stats: {data.get('game', {}).get('home', {}).get('stats')}")
            print(f"Away Team Stats: {data.get('game', {}).get('away', {}).get('stats')}")
            
            home_players = data.get('home_players', [])
            away_players = data.get('away_players', [])
            
            print(f"\n=== PLAYER STATS ===")
            print(f"Home Players Count: {len(home_players)}")
            print(f"Away Players Count: {len(away_players)}")
            
            if home_players:
                print(f"\nFirst Home Player:")
                print(json.dumps(home_players[0], indent=2))
            
            if away_players:
                print(f"\nFirst Away Player:")
                print(json.dumps(away_players[0], indent=2))
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test_endpoint())
