import asyncio
import json
from datetime import datetime, timedelta
from backend.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models import GameUpcoming

async def test():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        result = await session.execute(
            select(GameUpcoming).where(
                (GameUpcoming.start_time >= today_start) & 
                (GameUpcoming.start_time < today_end)
            ).order_by(GameUpcoming.start_time)
        )
        games = result.scalars().all()
        
        games_list = []
        for game in games:
            game_dict = {
                "game_id": game.game_id,
                "sport": (game.sport or "Unknown").upper(),
                "start_time": game.start_time.isoformat() if game.start_time else None,
            }
            games_list.append(game_dict)
        
        print(json.dumps(games_list, indent=2))

asyncio.run(test())
