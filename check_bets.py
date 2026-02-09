import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('sports_intel.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check the 16 bets
cursor.execute("""
    SELECT id, parlay_id, game_id, selection, status, stake, original_stake, placed_at
    FROM bets
    ORDER BY placed_at DESC
    LIMIT 16
""")

bets = cursor.fetchall()
print("Latest 16 bets:")
for bet in bets:
    print(f"  ID: {bet['id']}, Parlay: {bet['parlay_id'][:8] if bet['parlay_id'] else 'None'}, "
          f"Game ID: {bet['game_id']}, Status: {bet['status']}, Placed: {bet['placed_at']}")

# Check if game_id is set
null_game_ids = sum(1 for b in bets if not b['game_id'])
print(f"\nBets with NULL game_id: {null_game_ids}/16")

# Check if there are games from yesterday
yesterday = (datetime.utcnow() - timedelta(days=1)).date()
cursor.execute("""
    SELECT COUNT(*) as count FROM games 
    WHERE DATE(scheduled_at) = DATE(?)
""", (yesterday,))
result = cursor.fetchone()
print(f"Games in DB from yesterday ({yesterday}): {result['count']}")

# Check if there are any finished games
cursor.execute("""
    SELECT COUNT(*) as count FROM games 
    WHERE status IN ('finished', 'live')
""")
result = cursor.fetchone()
print(f"Finished or live games in DB: {result['count']}")

conn.close()
