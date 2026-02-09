#!/usr/bin/env python3
"""
Manually link bets to placeholder game records
"""
import sqlite3

conn = sqlite3.connect('/Users/dakotanicol/sports_betting_dashboard/sports_intel.db')
cursor = conn.cursor()

# Get all pending bets with no game_id
cursor.execute("""
    SELECT id, selection, raw_text FROM bets 
    WHERE game_id IS NULL AND status = 'pending'
    ORDER BY id DESC
    LIMIT 20
""")

pending_bets = cursor.fetchall()
print(f"Found {len(pending_bets)} pending bets\n")

# Manual game mapping
game_ids = {
    'Celtics': 'celtics-heat-20260206',
    'Heat': 'celtics-heat-20260206',
    'Bucks': 'bucks-pacers-20260206',
    'Pacers': 'bucks-pacers-20260206',
    'Anthony Edwards': 'timberwolves-pelicans-20260206',
    'Timberwolves': 'timberwolves-pelicans-20260206',
    'Pelicans': 'timberwolves-pelicans-20260206',
    'Kings': 'kings-clippers-20260206',
    'Clippers': 'kings-clippers-20260206',
    'De\'Aaron Fox': 'kings-clippers-20260206',
    'UConn': 'stjohns-uconn-20260206',
    "St. John's": 'stjohns-uconn-20260206',
    'Stephon Castle': 'stjohns-uconn-20260206',
    'Leeds': 'leeds-nottingham-20260206',
    'Nottingham': 'leeds-nottingham-20260206',
    'Derrick White': 'celtics-heat-20260206',
}

# Link each bet to a game
updated = 0
for bet_id, selection, raw_text in pending_bets:
    game_id = None
    
    # Try to match based on selection
    for team_name, gid in game_ids.items():
        if team_name.lower() in selection.lower():
            game_id = gid
            break
    
    # If not found, try raw_text
    if not game_id:
        for team_name, gid in game_ids.items():
            if team_name.lower() in raw_text.lower():
                game_id = gid
                break
    
    if game_id:
        cursor.execute("UPDATE bets SET game_id = ? WHERE id = ?", (game_id, bet_id))
        print(f"✅ Bet {bet_id} ({selection[:40]}) → {game_id}")
        updated += 1
    else:
        print(f"❌ Bet {bet_id} ({selection[:40]}) - NO MATCH")

if updated > 0:
    conn.commit()
    print(f"\n✅ Updated {updated} bets with game_ids")
else:
    print("\n❌ No bets were updated")

conn.close()
