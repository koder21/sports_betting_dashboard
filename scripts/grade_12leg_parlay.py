#!/usr/bin/env python3
"""Grade the 12-leg parlay."""

import sqlite3
from datetime import datetime

conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    parlay_id = 'dc7851eb-36d4-4ca0-82ac-2dedbc51129a'
    
    # Get all legs of the parlay
    cursor.execute("""
        SELECT 
            id, 
            game_id, 
            selection,
            stake,
            odds,
            original_stake
        FROM bets 
        WHERE parlay_id = ?
        ORDER BY id
    """, (parlay_id,))
    
    legs = cursor.fetchall()
    
    print(f"Grading 12-leg parlay {parlay_id}\n")
    print(f"Found {len(legs)} legs:\n")
    
    all_won = True
    parlay_odds = 1.0
    
    for i, leg in enumerate(legs, 1):
        print(f"Leg {i}: {leg['selection']}")
        
        # Get game result
        cursor.execute("""
            SELECT home_team_name, away_team_name, home_score, away_score, status
            FROM games 
            WHERE game_id = ?
        """, (leg['game_id'],))
        
        game = cursor.fetchone()
        
        if not game:
            print(f"  ✗ Game not found")
            all_won = False
            continue
        
        # Check if game is final
        status_lower = game['status'].lower() if game['status'] else ""
        is_final = (status_lower == "final" or "final" in status_lower or 
                   game['status'] in ("STATUS_FINAL", "STATUS_FULL_TIME"))
        
        if not is_final:
            print(f"  ⚠ Game not final yet (status: {game['status']})")
            all_won = False
            continue
        
        # Extract team name from selection
        team_name = leg['selection'].split()[0].lower()
        home_lower = (game['home_team_name'] or "").lower()
        away_lower = (game['away_team_name'] or "").lower()
        
        # Determine if bet was on home or away
        bet_on_home = team_name in home_lower or home_lower in team_name
        bet_on_away = team_name in away_lower or away_lower in team_name
        
        if not (bet_on_home or bet_on_away):
            print(f"  ✗ Team not matched (looking for '{team_name}')")
            all_won = False
            continue
        
        # Determine if bet won
        home_won = game['home_score'] > game['away_score']
        
        if bet_on_home:
            won = home_won
        else:
            won = not home_won
        
        status = "won" if won else "lost"
        parlay_odds *= leg['odds']
        
        if not won:
            all_won = False
        
        result_icon = "✓" if won else "✗"
        print(f"  {result_icon} {status.upper()}")
        print(f"    {game['home_team_name']} {game['home_score']} - {game['away_score']} {game['away_team_name']}")
        print()
        
        # Update individual leg
        leg_status = "won" if won else "lost"
        cursor.execute("""
            UPDATE bets 
            SET status = ?, graded_at = ?
            WHERE id = ?
        """, (leg_status, datetime.utcnow().isoformat(), leg['id']))
    
    # Determine parlay status
    parlay_status = "won" if all_won else "lost"
    
    # Calculate profit for each leg
    if all_won:
        original_stake = legs[0]['original_stake']
        total_profit = original_stake * (parlay_odds - 1)
        profit_per_leg = total_profit / len(legs)
    else:
        stake_per_leg = legs[0]['original_stake'] / len(legs)
        profit_per_leg = -stake_per_leg
    
    # Update all legs with profit
    cursor.execute("""
        UPDATE bets 
        SET profit = ?
        WHERE parlay_id = ?
    """, (profit_per_leg, parlay_id))
    
    conn.commit()
    
    print("="*60)
    print(f"\nParlay Result: {parlay_status.upper()}")
    print(f"Profit per leg: ${profit_per_leg:+.2f}")
    print(f"Total profit: ${profit_per_leg * len(legs):+.2f}")
    print("\n✓ Parlay graded successfully")

finally:
    cursor.close()
    conn.close()
