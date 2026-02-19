#!/usr/bin/env python3
"""
Update parlay_odds for all parlays in the PostgreSQL bets table.
Calculates true parlay odds from leg odds (American or decimal) and updates all legs.
"""
import psycopg2
import math

# Connect to your PostgreSQL database
conn = psycopg2.connect(dbname="sports_intel", user="sbd", password="sbddb", host="localhost", port=5432)
cur = conn.cursor()

# Get all unique parlay_ids
cur.execute("SELECT DISTINCT parlay_id FROM bets WHERE parlay_id IS NOT NULL;")
parlay_ids = [row[0] for row in cur.fetchall()]

for parlay_id in parlay_ids:
    cur.execute("SELECT odds FROM bets WHERE parlay_id = %s;", (parlay_id,))
    leg_odds = [float(row[0]) for row in cur.fetchall()]
    if not leg_odds or len(leg_odds) < 2:
        continue  # Only update for true parlays

    # Convert all odds to decimal odds
    decimal_odds = []
    for odds in leg_odds:
        if odds >= 1.01 and odds < 20:  # Already decimal odds
            decimal_odds.append(odds)
        elif odds > 0:
            decimal_odds.append((odds / 100) + 1)
        else:
            decimal_odds.append((100 / abs(odds)) + 1)

    # Multiply all decimal odds
    product = 1.0
    for d in decimal_odds:
        product *= d

    # Convert back to American odds
    if product >= 2.0:
        parlay_odds = (product - 1) * 100
    else:
        parlay_odds = -100 / (product - 1)

    # Update all legs in this parlay
    cur.execute("UPDATE bets SET parlay_odds = %s WHERE parlay_id = %s;", (parlay_odds, parlay_id))
    print(f"Updated parlay {parlay_id[:8]}: parlay_odds={parlay_odds:.2f}")

conn.commit()
cur.close()
conn.close()
print("✅ All parlay_odds updated.")
