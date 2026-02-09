#!/usr/bin/env python3
"""
Backfill EPL (English Premier League) soccer player stats for the last 365 days
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
from backend.models.player import Player
from backend.models.team import Team


async def main():
    print("=" * 80)
    print("EPL Player Stats Backfill - Last 6 Months")
    print("=" * 80)
    
    # Calculate date range (last 6 months to match NFL)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\nDate Range: {start_date.date()} to {end_date.date()}")
    print(f"Clearing existing EPL player stats...")
    
    async with AsyncSessionLocal() as session:
        # Delete existing EPL stats
        result = await session.execute(
            delete(PlayerStats).where(PlayerStats.sport == "EPL")
        )
        deleted_count = result.rowcount
        await session.commit()
        print(f"✅ Deleted {deleted_count} existing EPL player stats")
    
    # Get all EPL games from the last 365 days
    print(f"\nFetching EPL games from ESPN...")
    client = ESPNClient()
    
    try:
        # EPL uses league code "eng.1" on ESPN
        all_game_ids = []
        
        # Try to get games by checking every 7 days over the past 6 months (faster)
        for days_ago in range(0, 180, 7):  # Check every 7 days going back 6 months
            check_date = end_date - timedelta(days=days_ago)
            date_str = check_date.strftime("%Y%m%d")
            
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates={date_str}"
            data = await client.get_json(url)
            
            if data and "events" in data:
                day_games = []
                for event in data["events"]:
                    game_id = event.get("id")
                    status = event.get("status", {}).get("type", {}).get("name", "")
                    
                    # Only get completed games
                    if game_id and status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                        day_games.append(game_id)
                        all_game_ids.append(game_id)
                
                if day_games:
                    print(f"  Found {len(day_games)} completed games on {check_date.date()}")
        
        print(f"\n📊 Total EPL games found: {len(all_game_ids)}")
        
        if not all_game_ids:
            print("❌ No completed EPL games found in the date range")
            await client.close()
            return
        
        # Now scrape player stats for each game
        print(f"\nScraping player stats for {len(all_game_ids)} games...")
        print("This may take a while...\n")
        
        total_players = 0
        successful_games = 0
        failed_games = 0
        
        async with AsyncSessionLocal() as session:
            for i, game_id in enumerate(all_game_ids, 1):
                try:
                    # Get game summary with player rosters and stats
                    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event={game_id}"
                    data = await client.get_json(url)
                    
                    if not data:
                        failed_games += 1
                        print(f"  [{i}/{len(all_game_ids)}] Game {game_id}: ❌ No data")
                        continue
                    
                    # Get rosters with player stats
                    rosters = data.get("rosters", [])
                    stats_added = 0
                    
                    for roster in rosters:
                        team = roster.get("team", {})
                        team_id = team.get("id")
                        team_name = team.get("displayName")
                        team_abbr = team.get("abbreviation")
                        
                        # Get team logo
                        team_logos = team.get("logos", [])
                        team_logo = team_logos[0].get("href") if team_logos else None
                        
                        # Insert/update team
                        if team_id:
                            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                            team_stmt = sqlite_insert(Team).values(
                                team_id=str(team_id),
                                espn_id=str(team_id),
                                name=team_name,
                                abbreviation=team_abbr,
                                sport_name="EPL",
                                league="eng.1",
                                logo=team_logo
                            )
                            team_stmt = team_stmt.on_conflict_do_update(
                                index_elements=['team_id'],
                                set_=dict(
                                    name=team_name,
                                    abbreviation=team_abbr,
                                    logo=team_logo
                                )
                            )
                            await session.execute(team_stmt)
                        
                        players = roster.get("roster", [])
                        
                        for player_entry in players:
                            athlete = player_entry.get("athlete", {})
                            player_id = athlete.get("id")
                            player_name = athlete.get("fullName")
                            position_data = player_entry.get("position", {})
                            position = position_data.get("abbreviation") if isinstance(position_data, dict) else None
                            jersey = player_entry.get("jersey")
                            
                            if not player_id or not player_name:
                                continue
                            
                            # Insert/update player
                            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                            player_stmt = sqlite_insert(Player).values(
                                player_id=str(player_id),
                                espn_id=str(player_id),
                                full_name=player_name,
                                name=player_name,
                                position=position,
                                team_id=str(team_id) if team_id else None,
                                sport="EPL",
                                league="eng.1",
                                jersey=jersey,
                                active=True
                            )
                            player_stmt = player_stmt.on_conflict_do_update(
                                index_elements=['player_id'],
                                set_=dict(
                                    full_name=player_name,
                                    name=player_name,
                                    position=position,
                                    team_id=str(team_id) if team_id else None,
                                    jersey=jersey,
                                    active=True
                                )
                            )
                            await session.execute(player_stmt)
                            
                            # Get stats for this player
                            stats = player_entry.get("stats", [])
                            if not stats:
                                continue
                            
                            # Parse soccer stats (using epl_ prefix to match table schema)
                            stat_dict = {}
                            for stat in stats:
                                name = stat.get("name")
                                value = stat.get("value", 0)
                                
                                if name == "goals":
                                    stat_dict["epl_goals"] = int(value) if value else None
                                elif name == "assists":
                                    stat_dict["epl_assists"] = int(value) if value else None
                                elif name == "shotsOnTarget":
                                    stat_dict["epl_shots_on_target"] = int(value) if value else None
                                elif name == "totalShots":
                                    # Store in a generic field if available, or skip
                                    pass  # No epl_shots field in schema
                                elif name == "foulsCommitted":
                                    # Store in a generic field if available, or skip
                                    pass  # No epl_fouls field in schema
                                elif name == "yellowCards":
                                    # Store in a generic field if available, or skip
                                    pass  # No epl_yellow_cards field in schema
                                elif name == "redCards":
                                    # Store in a generic field if available, or skip
                                    pass  # No epl_red_cards field in schema
                                elif name == "saves":
                                    stat_dict["epl_saves"] = int(value) if value else None
                                elif name == "accuratePasses":
                                    stat_dict["epl_passes"] = int(value) if value else None
                                elif name == "tackles":
                                    stat_dict["epl_tackles"] = int(value) if value else None
                            
                            # Insert player stat
                            from sqlalchemy.dialects.sqlite import insert
                            stmt = insert(PlayerStats).values(
                                game_id=game_id,
                                player_id=str(player_id),
                                team_id=str(team_id),
                                sport="EPL",
                                league="eng.1",
                                **stat_dict
                            )
                            # Use prefix_with to handle duplicates (skip if exists)
                            stmt = stmt.prefix_with("OR IGNORE")
                            await session.execute(stmt)
                            stats_added += 1
                    
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
