import asyncio
from backend.config import settings
from backend.db import get_session
from backend.models.game import Game

from sqlalchemy import select

def is_non_final(status):
    if not status:
        return True
    status_lower = status.lower()
    finished_keywords = [
        "final", "full-time", "ft", "final overtime", "final/ot", "final ot",
        "status_final", "status_full_time", "status_ft", "status_final overtime",
        "status_final/ot", "status_final ot"
    ]
    return not any(k in status_lower for k in finished_keywords)

async def main():
    async with get_session() as session:
        result = await session.execute(select(Game))
        games = result.scalars().all()
        non_final_games = [g for g in games if is_non_final(g.status)]
        print(f"Found {len(non_final_games)} non-final games:")
        for g in non_final_games:
            print(f"ID: {g.game_id}, Status: {g.status}, Teams: {g.home_team_name} vs {g.away_team_name}, Start: {g.start_time}")

if __name__ == "__main__":
    asyncio.run(main())
