#!/usr/bin/env python3
import asyncio
import httpx

async def test_game_endpoint():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:8000/api/games/401810616/detailed')
        data = response.json()
        print(f"total_bets: {data.get('total_bets')}")
        print(f"bets count: {len(data.get('bets', []))}")
        print(f"Keys in response: {list(data.keys())}")

asyncio.run(test_game_endpoint())
