import psycopg2

conn = psycopg2.connect(dbname='sports_intel', user='dakotanicol')
cursor = conn.cursor()

# Find all NBA_ team_ids and their numeric suffix
cursor.execute("SELECT team_id FROM teams WHERE team_id LIKE 'NBA_%'")
rows = cursor.fetchall()

for (team_id,) in rows:
    parts = team_id.split('_')
    if len(parts) != 2 or not parts[1].isdigit():
        print(f"Warning: Skipping malformed team_id '{team_id}'")
        continue
    numeric = parts[1]
    new_id = f'NBA-{numeric}'
    # Only update if NBA-<numeric> exists
    cursor.execute("SELECT team_id FROM teams WHERE team_id = %s", (new_id,))
    if cursor.fetchone():
        # Remove NBA_ row
        cursor.execute("DELETE FROM teams WHERE team_id = %s", (team_id,))
        print(f"Deleted {team_id}, kept {new_id}")
    else:
        # Rename NBA_ to NBA-
        cursor.execute("UPDATE teams SET team_id = %s WHERE team_id = %s", (new_id, team_id))
        print(f"Renamed {team_id} to {new_id}")

conn.commit()
cursor.close()
conn.close()
print("NBA team_id cleanup complete.")
