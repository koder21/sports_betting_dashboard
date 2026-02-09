import asyncio
from backend.db import AsyncSessionLocal
from sqlalchemy import select, func
from backend.models.player_stats import PlayerStats
from backend.models.player import Player

async def main():
    async with AsyncSessionLocal() as session:
        # Check player stats
        stats_result = await session.execute(
            select(PlayerStats.sport, func.count(PlayerStats.id))
            .group_by(PlayerStats.sport)
            .order_by(PlayerStats.sport)
        )
        print('Player Stats by Sport:')
        total_stats = 0
        for sport, count in stats_result.all():
            print(f'  {sport}: {count:,}')
            total_stats += count
        print(f'  TOTAL: {total_stats:,}')
        
        # Check players to see if rosters are being added
        print()
        players_result = await session.execute(
            select(Player.sport, func.count(Player.player_id))
            .group_by(Player.sport)
            .order_by(Player.sport)
        )
        print('Players by Sport:')
        total_players = 0
        for sport, count in players_result.all():
            print(f'  {sport}: {count:,}')
            total_players += count
        print(f'  TOTAL: {total_players:,}')

if __name__ == "__main__":
    asyncio.run(main())
