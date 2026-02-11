#!/usr/bin/env python3
"""Remove duplicate GameResult records."""

import sqlite3

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
cursor = conn.cursor()

try:
    # Get duplicate game_ids
    cursor.execute("""
        SELECT game_id, COUNT(*) as cnt FROM games_results 
        GROUP BY game_id HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate game_ids:")
        for game_id, count in duplicates:
            print(f"  {game_id}: {count} records")
        
        # For each duplicate, keep the first and delete the rest
        for game_id, _ in duplicates:
            cursor.execute(f"""
                DELETE FROM games_results 
                WHERE game_id = ? 
                AND rowid NOT IN (
                    SELECT MIN(rowid) FROM games_results 
                    WHERE game_id = ?
                )
            """, (game_id, game_id))
        
        conn.commit()
        print("\nDuplicate records removed!")
    else:
        print("No duplicate game_ids found.")
finally:
    cursor.close()
    conn.close()
