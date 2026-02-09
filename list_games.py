#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/Users/dakotanicol/sports_betting_dashboard/sports_intel.db')
cursor = conn.cursor()

# First, list what games exist
cursor.execute("SELECT game_id, home_team_name, away_team_name, sport FROM games WHERE sport IS NOT NULL ORDER BY sport")
games = cursor.fetchall()

print(f"Total games in DB: {len(games)}\n")
print("Available games:")
for game in games:
    if game[3]:  # sport
        print(f"  {game[3].upper()}: {game[2]} @ {game[1]}")
        print(f"    ID: {game[0]}\n")

conn.close()
