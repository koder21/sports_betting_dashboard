import asyncio
import json
from backend.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models import GameLive

async def test():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(GameLive))
        games = result.scalars().all()
        
        response = []
        for game in games:
            game_dict = {
                "game_id": game.game_id,
                "home_score": game.home_score or 0,
                "away_score": game.away_score or 0,
                "home_team": game.home_team_name or "Home Team",
                "away_team": game.away_team_name or "Away Team",
                "sport": (game.sport or "Unknown").upper(),
                "status": game.status or "unknown",
            }
            if game.period is not None:
                game_dict["period"] = game.period
            if game.clock is not None:
                game_dict["clock"] = game.clock
            if game.possession is not None:
                game_dict["possession"] = game.possession
            response.append(game_dict)
        
        print(json.dumps(response, indent=2))

asyncio.run(test())
