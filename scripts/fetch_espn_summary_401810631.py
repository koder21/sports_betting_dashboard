import asyncio
from backend.services.espn_client import ESPNClient

async def main():
    game_id = "401810631"
    sport_type = "basketball"
    league = "nba"
    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
    client = ESPNClient()
    summary = await client.get_json(summary_url)
    print(f"ESPN summary for game {game_id}: {summary}")
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
