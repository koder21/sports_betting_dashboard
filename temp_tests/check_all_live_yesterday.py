import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime
from backend.models.games_live import GameLive
from backend.models.game import Game
from backend.config import settings

async def check_games():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Get ALL games from yesterday
        all_live = await session.execute(
            select(GameLive)
            .join(Game, GameLive.game_id == Game.game_id)
            .where(
                Game.start_time >= datetime(2026, 2, 9, 8, 0, 0),
                Game.start_time < datetime(2026, 2, 10, 8, 0, 0)
            )
            .order_by(Game.start_time)
        )
        games = all_live.scalars().all()
        print(f"Total GameLive records from yesterday: {len(games)}")
        for g in games:
            print(f"  - {g.away_team_name} @ {g.home_team_name} | Status: {g.status}")

asyncio.run(check_games())
