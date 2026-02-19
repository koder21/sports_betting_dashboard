import asyncio
from backend.db import get_session
from backend.models.games_results import GameResult
from backend.services.espn_client import ESPNClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def main():
    game_id = "401810631"
    sport_type = "basketball"
    league = "nba"
    sport_upper = "NBA"
    client = ESPNClient()
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
    summary = await client.get_json(summary_url)
    competitions = summary.get('competitions', [{}])[0]
    home_team = competitions.get('home', {}).get('team', {})
    away_team = competitions.get('away', {}).get('team', {})
    start_time = competitions.get('date')
    status = competitions.get('status', {}).get('type', {}).get('name')
    league_val = competitions.get('league', {}).get('abbreviation', league)
    async with get_session() as session:
        await session.execute(
            pg_insert(GameResult).values(
                game_id=game_id,
                sport=sport_upper,
                league=league_val,
                start_time=start_time,
                home_team_id=home_team.get('id'),
                away_team_id=away_team.get('id'),
                home_team_name=home_team.get('displayName'),
                away_team_name=away_team.get('displayName'),
                status=status,
            ).on_conflict_do_nothing(index_elements=['game_id'])
        )
        await session.commit()
    await client.close()
    print("Upserted games_results row for game 401810631.")

if __name__ == "__main__":
    asyncio.run(main())
