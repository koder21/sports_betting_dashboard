import asyncio
import json
from backend.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models import GameUpcoming

async def test():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        sport_id = 1
        SPORTS = {
            1: "nba",
            2: "nfl",
            3: "nhl",
            4: "ncaab",
            5: "epl",
        }
        
        sport_name = SPORTS.get(sport_id, "").lower()
        print(f"Looking for sport: {sport_name}")
        
        result = await session.execute(
            select(GameUpcoming)
            .where(GameUpcoming.sport == sport_name if sport_name else False)
            .order_by(GameUpcoming.start_time)
        )
        games = result.scalars().all()
        
        print(f"Found {len(games)} games")
        
        games_list = []
        for game in games:
            game_dict = {
                "game_id": game.game_id,
                "sport": (game.sport or "Unknown").lower(),
                "start_time": game.start_time.isoformat() if game.start_time else None,
                "home_team": game.home_team_name,
                "away_team": game.away_team_name,
                "status": game.status,
            }
            games_list.append(game_dict)
        
        print(json.dumps(games_list[:3], indent=2))

asyncio.run(test())
