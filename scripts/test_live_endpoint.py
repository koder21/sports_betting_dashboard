import asyncio
import sys
import json
sys.path.insert(0, '.')

async def test():
    from sqlalchemy import select
    from backend.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from backend.models import GameLive
    from backend.utils.json import to_primitive
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(GameLive))
        live_games = result.scalars().all()
        
        games_list = []
        for game in live_games:
            game_dict = {
                "game_id": game.game_id,
                "home_score": game.home_score or 0,
                "away_score": game.away_score or 0,
                "status": "in",
                "period": game.period,
                "clock": game.clock,
                "possession": game.possession,
                "sport": game.sport or "Unknown",
            }
            games_list.append(game_dict)
        
        result_data = to_primitive(games_list)
        print(f"Games list before to_primitive: {games_list}")
        print(f"Result after to_primitive: {result_data}")
        print(json.dumps(result_data, indent=2))

asyncio.run(test())
