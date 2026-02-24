#!/usr/bin/env python3
"""Check manually placed bets."""

import sqlite3

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # Get some completed bets to see their structure
    cursor.execute("""
        SELECT DISTINCT bet_type, COUNT(*) as count
        FROM bets 
        WHERE status IN ('won', 'lost')
        GROUP BY bet_type
        ORDER BY count DESC
    """)
    
    print("Graded bets by type:")
    for row in cursor.fetchall():
        print(f"  {row['bet_type']}: {row['count']}")
    
    print("\n" + "="*60)
    
    # Get pending bets by type
    cursor.execute("""
        SELECT DISTINCT bet_type, COUNT(*) as count
        FROM bets 
        WHERE status = 'pending'
        GROUP BY bet_type
        ORDER BY count DESC
    """)
    
    print("\nPending bets by type:")
    for row in cursor.fetchall():
        print(f"  {row['bet_type']}: {row['count']}")

finally:
    cursor.close()
    conn.close()
