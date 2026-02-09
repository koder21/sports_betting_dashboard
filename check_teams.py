import sqlite3
conn = sqlite3.connect('sports_intel.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT team_id, espn_id, name FROM teams')
for row in c.fetchall():
    print(f"team_id={row['team_id']}, espn_id={row['espn_id']}, name={row['name']}")
