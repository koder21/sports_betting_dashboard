#!/usr/bin/env python3
"""Fetch today's slate of games from ESPN"""
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.espn_client import ESPNClient
import sqlite3

SPORTS = [
    ("basketball", "nba", "NBA"),
    ("basketball", "mens-college-basketball", "NCAAB"),
    ("football", "nfl", "NFL"),
    ("hockey", "nhl", "NHL"),
    ("soccer", "eng.1", "EPL"),
]


async def fetch_todays_games():
    client = ESPNClient()
    
    # Get today's date in YYYYMMDD format
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    all_games = []
    
    for sport_type, league, sport_name in SPORTS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard?dates={today}"
        data = await client.get_json(url)
        
        if not data:
            continue
        
        events = data.get("events", [])
        print(f"\n{sport_name}: {len(events)} games")
        
        for event in events:
            game_id = event.get("id")
            status = event.get("status", {})
            status_type = status.get("type", {}).get("name", "")
            status_detail = status.get("type", {}).get("detail", "")
            
            competitions = event.get("competitions", [])
            if not competitions:
                continue
            
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            
            home_team = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away_team = next((c for c in competitors if c.get("homeAway") == "away"), None)
            
            if not home_team or not away_team:
                continue
            
            home_team_name = home_team.get("team", {}).get("displayName", "Unknown")
            away_team_name = away_team.get("team", {}).get("displayName", "Unknown")
            home_score = int(home_team.get("score", 0))
            away_score = int(away_team.get("score", 0))
            
            # Get start time
            date_str = event.get("date", "")
            
            game_info = {
                "sport": sport_name,
                "game_id": game_id,
                "away_team": away_team_name,
                "home_team": home_team_name,
                "status": status_type,
                "status_detail": status_detail,
                "away_score": away_score,
                "home_score": home_score,
                "start_time": date_str,
            }
            
            all_games.append(game_info)
            
            # Print game info
            if status_type == "STATUS_IN_PROGRESS":
                period = status.get("period", "")
                clock = status.get("displayClock", "")
                print(f"  🔴 LIVE: {away_team_name} {away_score} @ {home_team_name} {home_score} (Q{period} {clock})")
            elif status_type in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                print(f"  ✅ FINAL: {away_team_name} {away_score} @ {home_team_name} {home_score}")
            else:
                print(f"  📅 {status_detail}: {away_team_name} @ {home_team_name}")
    
    print(f"\n📊 Total games today: {len(all_games)}")
    
    # Now update games_live with live games only
    db = sqlite3.connect("sports_intel.db")
    cursor = db.cursor()
    cursor.execute("DELETE FROM games_live")
    
    live_count = 0
    for game in all_games:
        if game["status"] == "STATUS_IN_PROGRESS":
            cursor.execute("""
                INSERT INTO games_live (game_id, home_team_name, away_team_name, home_score, 
                                       away_score, sport, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (game["game_id"], game["home_team"], game["away_team"], 
                  game["home_score"], game["away_score"], game["sport"]))
            live_count += 1
    
    db.commit()
    db.close()
    
    print(f"✅ Updated {live_count} live games in database")


if __name__ == "__main__":
    asyncio.run(fetch_todays_games())
