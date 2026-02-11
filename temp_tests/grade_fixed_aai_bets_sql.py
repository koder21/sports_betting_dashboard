#!/usr/bin/env python3
"""Manually grade the fixed AAI bets using direct SQL queries."""

import sqlite3
from datetime import datetime

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # Get the AAI bets that we just fixed
    cursor.execute("""
        SELECT 
            id, 
            game_id, 
            selection,
            stake,
            odds
        FROM bets 
        WHERE status = 'pending' 
        AND bet_type = 'moneyline'
        AND reason LIKE '%AAI%'
    """)
    
    aai_bets = cursor.fetchall()
    
    print(f"Found {len(aai_bets)} AAI bets to grade:\n")
    
    for bet in aai_bets:
        print(f"Grading Bet {bet['id']}: {bet['selection']}")
        
        # Get game result
        cursor.execute("""
            SELECT home_team_name, away_team_name, home_score, away_score, status
            FROM games 
            WHERE game_id = ?
        """, (bet['game_id'],))
        
        game = cursor.fetchone()
        
        if not game:
            print(f"  ✗ Game not found")
            continue
        
        # Check if game is final
        status_lower = game['status'].lower() if game['status'] else ""
        if "final" not in status_lower and "full time" not in status_lower:
            print(f"  ⚠ Game not final yet (status: {game['status']})")
            continue
        
        # Extract team name from selection
        team_name = bet['selection'].split()[0].lower()
        home_lower = (game['home_team_name'] or "").lower()
        away_lower = (game['away_team_name'] or "").lower()
        
        # Determine if bet was on home or away
        bet_on_home = team_name in home_lower or home_lower in team_name
        bet_on_away = team_name in away_lower or away_lower in team_name
        
        if not (bet_on_home or bet_on_away):
            print(f"  ✗ Team not matched (looking for '{team_name}')")
            continue
        
        # Determine if bet won
        home_won = game['home_score'] > game['away_score']
        
        if bet_on_home:
            won = home_won
        else:
            won = not home_won
        
        status = "won" if won else "lost"
        
        # Calculate profit
        if won:
            if bet['odds'] > 0:
                profit = bet['stake'] * (bet['odds'] / 100)
            else:
                profit = bet['stake'] / (abs(bet['odds']) / 100)
        else:
            profit = -bet['stake']
        
        # Update bet in database
        cursor.execute("""
            UPDATE bets 
            SET status = ?, profit = ?, graded_at = ?
            WHERE id = ?
        """, (status, profit, datetime.utcnow().isoformat(), bet['id']))
        
        result_text = f"{'WON' if won else 'LOST'}"
        print(f"  ✓ {result_text}")
        print(f"    Game: {game['home_team_name']} {game['home_score']} - {game['away_score']} {game['away_team_name']}")
        print(f"    Profit/Loss: ${profit:+.2f}")
        print()
    
    conn.commit()
    print("✓ Bets graded successfully")

finally:
    cursor.close()
    conn.close()
