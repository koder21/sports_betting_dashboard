#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("sports_intel.db")
cursor = conn.cursor()

# Insert game 740838: Brighton 0 - 1 Crystal Palace
cursor.execute("""
    INSERT OR REPLACE INTO games_results 
    (game_id, sport, start_time, status, home_team_id, away_team_id, home_team, away_team, home_score, away_score)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", ('740838', 'EPL', '2026-02-08 14:00:00', 'STATUS_FULL_TIME', '331', '384', 'Brighton & Hove Albion', 'Crystal Palace', 0, 1))

# Insert game 740845: Liverpool 1 - 2 Manchester City
cursor.execute("""
    INSERT OR REPLACE INTO games_results 
    (game_id, sport, start_time, status, home_team_id, away_team_id, home_team, away_team, home_score, away_score)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", ('740845', 'EPL', '2026-02-08 16:30:00', 'STATUS_FULL_TIME', '364', '382', 'Liverpool', 'Manchester City', 1, 2))

conn.commit()
print("✅ Inserted final game results for both games")

# Verify
cursor.execute("SELECT game_id, home_team, away_team, home_score, away_score FROM games_results WHERE game_id IN ('740838', '740845')")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
