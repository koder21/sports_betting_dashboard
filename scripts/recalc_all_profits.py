#!/usr/bin/env python3
"""
Recalculate and update profit for all finished bets and parlays using the current decimal odds.
Run this after fixing odds in the database to update all historical P&L.
"""
import psycopg2

conn = psycopg2.connect(dbname="sports_intel", user="sbd", password="sbddb", host="localhost", port=5432)
cur = conn.cursor()

# Update all bets with status 'won' or 'lost' (regardless of parlay_id)
cur.execute("""
    SELECT id, stake, odds, status FROM bets WHERE status IN ('won', 'lost')
""")
for bet_id, stake, odds, status in cur.fetchall():
    stake = float(stake)
    odds = float(odds)
    if status == 'won':
        # Always use decimal odds
        profit = (stake * odds) - stake
    elif status == 'lost':
        profit = -stake
    else:
        continue
    print(f"[DEBUG] bet_id={bet_id}, stake={stake}, odds={odds}, calculated profit={profit}")
    cur.execute("UPDATE bets SET profit = %s WHERE id = %s", (profit, bet_id))
    print(f"Updated bet {bet_id}: profit={profit:.2f}")

# Update parlays (all legs)
cur.execute("""
    SELECT DISTINCT parlay_id FROM bets WHERE parlay_id IS NOT NULL
""")
for (parlay_id,) in cur.fetchall():
    cur.execute("SELECT id, original_stake, parlay_odds, status FROM bets WHERE parlay_id = %s", (parlay_id,))
    legs = cur.fetchall()
    if not legs:
        continue
    statuses = [l[3] for l in legs]
    original_stake = float(legs[0][1])
    parlay_odds = legs[0][2]
    if parlay_odds is None:
        print(f"Skipped parlay {parlay_id[:8]}: parlay_odds is None")
        continue
    parlay_odds = float(parlay_odds)
    if all(s == 'won' for s in statuses):
        # Parlay win
        profit = (original_stake * parlay_odds) - original_stake
    else:
        # Parlay loss
        profit = -original_stake
    profit_per_leg = profit / len(legs)
    for leg_id, *_ in legs:
        cur.execute("UPDATE bets SET profit = %s WHERE id = %s", (profit_per_leg, leg_id))
    print(f"Updated parlay {parlay_id[:8]}: profit={profit:.2f}")

conn.commit()
cur.close()
conn.close()
print("✅ All finished bets and parlays recalculated with correct decimal odds.")
