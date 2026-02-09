#!/usr/bin/env python3
"""Refresh live games from ESPN APIs"""
import asyncio
import sys
from datetime import datetime, UTC
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


async def fetch_live_games():
    client = ESPNClient()
    db = sqlite3.connect("sports_intel.db")
    cursor = db.cursor()
    
    # Clear old live games
    cursor.execute("DELETE FROM games_live")
    
    live_count = 0
    
    for sport_type, league, sport_name in SPORTS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard"
        data = await client.get_json(url)
        
        if not data:
            continue
        
        events = data.get("events", [])
        
        for event in events:
            status_type = event.get("status", {}).get("type", {}).get("name", "")
            
            # Only include live games
            if status_type not in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]:
                continue
            
            game_id = event.get("id")
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
            
            # Get period and clock
            status = event.get("status", {})
            period = status.get("period")
            clock = status.get("displayClock", "")
            
            # Insert into games_live
            cursor.execute("""
                INSERT INTO games_live (game_id, home_team_name, away_team_name, home_score, 
                                       away_score, period, clock, sport, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, home_team_name, away_team_name, home_score, away_score, 
                  period, clock, sport_name, datetime.now(UTC).isoformat()))
            
            live_count += 1
            print(f"  {sport_name}: {away_team_name} @ {home_team_name} - {away_score}-{home_score} (Q{period} {clock})")
    
    db.commit()
    db.close()
    
    print(f"\n✅ Updated {live_count} live games")


if __name__ == "__main__":
    asyncio.run(fetch_live_games())
