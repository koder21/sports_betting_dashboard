#!/usr/bin/env python3
"""Check pending AAI bets in the database."""

import sqlite3

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # Get pending bets that have "AAI" in the reason
    cursor.execute("""
        SELECT 
            id, 
            placed_at, 
            game_id, 
            bet_type, 
            selection, 
            stake, 
            odds, 
            status,
            reason,
            player_id,
            parlay_id
        FROM bets 
        WHERE status = 'pending' AND reason LIKE '%AAI%'
        ORDER BY placed_at DESC
        LIMIT 10
    """)
    
    aai_bets = cursor.fetchall()
    
    if aai_bets:
        print(f"Found {len(aai_bets)} pending AAI bets:\n")
        for row in aai_bets:
            print(f"Bet ID: {row['id']}")
            print(f"  Game ID: {row['game_id']}")
            print(f"  Type: {row['bet_type']}")
            print(f"  Selection: {row['selection']}")
            print(f"  Stake: ${row['stake']}")
            print(f"  Odds: {row['odds']}")
            print(f"  Status: {row['status']}")
            print(f"  Player ID: {row['player_id']}")
            print(f"  Parlay ID: {row['parlay_id']}")
            print(f"  Reason: {row['reason'][:80]}...")
            print()
    else:
        print("No pending AAI bets found")
    
    # Also check the game status for those games
    if aai_bets:
        print("\n" + "="*60)
        print("Game statuses for these bets:\n")
        for row in aai_bets:
            if row['game_id']:
                cursor.execute("""
                    SELECT game_id, home_team_name, away_team_name, status, home_score, away_score
                    FROM games 
                    WHERE game_id = ?
                """, (row['game_id'],))
                game = cursor.fetchone()
                if game:
                    print(f"Game {game['game_id']}: {game['home_team_name']} vs {game['away_team_name']}")
                    print(f"  Status: {game['status']}")
                    print(f"  Score: {game['home_score']} - {game['away_score']}")
                    print()

finally:
    cursor.close()
    conn.close()
