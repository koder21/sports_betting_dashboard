#!/usr/bin/env python3
"""
Convert all parlay_odds in the PostgreSQL bets table to decimal odds.
If parlay_odds is American, convert to decimal. If already decimal, leave as is.
"""
import psycopg2

conn = psycopg2.connect(dbname="sports_intel", user="sbd", password="sbddb", host="localhost", port=5432)
cur = conn.cursor()

# Get all unique parlay_ids and their parlay_odds
cur.execute("SELECT DISTINCT parlay_id FROM bets WHERE parlay_id IS NOT NULL;")
parlay_ids = [row[0] for row in cur.fetchall()]

for parlay_id in parlay_ids:
    cur.execute("SELECT parlay_odds FROM bets WHERE parlay_id = %s LIMIT 1;", (parlay_id,))
    row = cur.fetchone()
    if not row or row[0] is None:
        continue
    parlay_odds = float(row[0])
    # Convert to decimal if needed
    if parlay_odds >= 1.01 and parlay_odds < 20:
        decimal_odds = parlay_odds  # Already decimal
    elif parlay_odds > 0:
        decimal_odds = (parlay_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(parlay_odds)) + 1
    cur.execute("UPDATE bets SET parlay_odds = %s WHERE parlay_id = %s;", (decimal_odds, parlay_id))
    print(f"Updated parlay {parlay_id[:8]}: parlay_odds(decimal)={decimal_odds:.4f}")

conn.commit()
cur.close()
conn.close()
print("✅ All parlay_odds converted to decimal odds.")
