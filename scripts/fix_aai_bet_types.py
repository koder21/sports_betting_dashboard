#!/usr/bin/env python3
"""Fix the existing AAI bets by changing their type from 'single' to 'moneyline'."""

import sqlite3

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
cursor = conn.cursor()

try:
    # Update pending AAI bets from 'single' to 'moneyline'
    cursor.execute("""
        UPDATE bets 
        SET bet_type = 'moneyline'
        WHERE status = 'pending' 
        AND bet_type = 'single'
        AND reason LIKE '%AAI%'
    """)
    
    rows_updated = cursor.rowcount
    conn.commit()
    
    if rows_updated > 0:
        print(f"✓ Updated {rows_updated} AAI bet(s) from 'single' to 'moneyline'")
        
        # Show the updated bets
        cursor.execute("""
            SELECT id, selection, stake, odds, bet_type, status
            FROM bets 
            WHERE status = 'pending' 
            AND reason LIKE '%AAI%'
        """)
        
        print("\nUpdated bets:")
        for row in cursor.fetchall():
            print(f"  Bet {row[0]}: {row[1]} (${row[2]} @ {row[3]}) - Type: {row[4]}")
    else:
        print("No AAI bets to update")

finally:
    cursor.close()
    conn.close()
