#!/usr/bin/env python3
"""
Backfill NFL player stats for the last 6 months
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.db import engine, AsyncSessionLocal
from backend.services.espn_client import ESPNClient
from backend.services.scraper_stats import PlayerStatsScraper
from sqlalchemy import select, delete
from backend.models.player_stats import PlayerStats


async def main():
    print("=" * 80)
    print("NFL Player Stats Backfill - Last 6 Months")
    print("=" * 80)
    
    # Calculate date range (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # ~6 months
    
    print(f"\nDate Range: {start_date.date()} to {end_date.date()}")
    print(f"Clearing existing NFL player stats...")
    
    async with AsyncSessionLocal() as session:
        # Delete existing NFL stats
        result = await session.execute(
            delete(PlayerStats).where(PlayerStats.sport == "NFL")
        )
        deleted_count = result.rowcount
        await session.commit()
        print(f"✅ Deleted {deleted_count} existing NFL player stats")
    
    # Get all NFL games from the last 6 months
    print(f"\nFetching NFL games from ESPN...")
    client = ESPNClient()
    
    try:
        # ESPN NFL calendar API to get all game dates in the season
        calendar_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        
        # Get games by fetching scoreboards for each week
        # NFL season 2025-2026 started around September 2025
        all_game_ids = []
        
        # Try to get games from recent weeks
        for days_ago in range(0, 180, 7):  # Check every 7 days going back 6 months
            check_date = end_date - timedelta(days=days_ago)
            date_str = check_date.strftime("%Y%m%d")
            
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_str}"
            data = await client.get_json(url)
            
            if data and "events" in data:
                week_games = []
                for event in data["events"]:
                    game_id = event.get("id")
                    status = event.get("status", {}).get("type", {}).get("name", "")
                    
                    # Only get completed games
                    if game_id and status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                        week_games.append(game_id)
                        all_game_ids.append(game_id)
                
                if week_games:
                    print(f"  Found {len(week_games)} completed games around {check_date.date()}")
        
        print(f"\n📊 Total NFL games found: {len(all_game_ids)}")
        
        if not all_game_ids:
            print("❌ No completed NFL games found in the date range")
            await client.close()
            return
        
        # Now scrape player stats for each game
        print(f"\nScraping player stats for {len(all_game_ids)} games...")
        print("This may take a while...\n")
        
        total_players = 0
        successful_games = 0
        failed_games = 0
        
        async with AsyncSessionLocal() as session:
            scraper = PlayerStatsScraper(client, session)
            
            for i, game_id in enumerate(all_game_ids, 1):
                try:
                    # Scrape boxscore for this game
                    stats_added = await scraper._scrape_game_boxscore(
                        game_id=game_id,
                        sport_type="football",
                        league="nfl",
                        sport_name="NFL"
                    )
                    
                    if stats_added > 0:
                        total_players += stats_added
                        successful_games += 1
                        print(f"  [{i}/{len(all_game_ids)}] Game {game_id}: ✅ {stats_added} players")
                    else:
                        failed_games += 1
                        print(f"  [{i}/{len(all_game_ids)}] Game {game_id}: ⚠️ No stats")
                    
                    # Commit every 10 games
                    if i % 10 == 0:
                        await session.commit()
                        print(f"\n  💾 Committed batch (Progress: {i}/{len(all_game_ids)})\n")
                    
                    # Small delay to be nice to ESPN API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    failed_games += 1
                    print(f"  [{i}/{len(all_game_ids)}] Game {game_id}: ❌ Error: {e}")
            
            # Final commit
            await session.commit()
            print(f"\n💾 Final commit complete")
    
    finally:
        await client.close()
    
    print("\n" + "=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"Total games processed: {len(all_game_ids)}")
    print(f"Successful: {successful_games}")
    print(f"Failed: {failed_games}")
    print(f"Total player stat records: {total_players}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
