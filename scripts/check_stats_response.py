#!/usr/bin/env python3
import httpx
import json

r = httpx.get('http://localhost:8000/games/401810626/detailed')
data = r.json()

print("=== GAME DETAILS ===")
print(f"Game ID: {data.get('game', {}).get('game_id')}")
print(f"Status: {data.get('game', {}).get('status')}")
print(f"Home: {data.get('game', {}).get('home', {}).get('team_name')}")
print(f"Away: {data.get('game', {}).get('away', {}).get('team_name')}")

print(f"\n=== TEAM STATS ===")
print(f"Home Stats: {data.get('game', {}).get('home', {}).get('stats')}")
print(f"Away Stats: {data.get('game', {}).get('away', {}).get('stats')}")

home_players = data.get('home_players', [])
away_players = data.get('away_players', [])

print(f"\n=== PLAYER COUNTS ===")
print(f"Home Players: {len(home_players)}")
print(f"Away Players: {len(away_players)}")

if home_players:
    print(f"\n=== FIRST HOME PLAYER ===")
    p = home_players[0]
    print(f"Name: {p.get('player_name')}")
    print(f"Points: {p.get('points')}")
    print(f"Rebounds: {p.get('rebounds')}")
    print(f"Assists: {p.get('assists')}")
