import sqlite3
import psycopg2
import json

# Paths and connection info
SQLITE_DB = 'backups/sports_intel.db'
PG_CONN = {
    'dbname': 'sports_intel',
    'user': 'sbd',
    'password': 'sbddb',
    'host': 'localhost',
    'port': 5432,
}

# List of tables to migrate in dependency order
TABLES = [
    'sports',
    'alerts',
    'bets',
    'games',
    'games_live',
    'games_results',  # games_results depends on games
    'games_upcoming',
    'injuries',
    'players',         # player_stats depends on players
    'teams',           # player_stats depends on teams
    'standings',
    'player_stats',    # depends on games_results, players, teams
]

def convert_value(val):
    if isinstance(val, bytes):
        return val.decode('utf-8')
    return val

def main():
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(**PG_CONN)
    pg_conn.autocommit = True
    pg_cur = pg_conn.cursor()
    
    for table in TABLES:
        print(f"Migrating {table}...")
        rows = sqlite_conn.execute(f'SELECT * FROM {table}').fetchall()
        if not rows:
            continue
        columns = [desc[0] for desc in sqlite_conn.execute(f'SELECT * FROM {table}').description]
        placeholders = ','.join(['%s'] * len(columns))
        insert_sql = f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
        # For player_stats, fetch all valid game_ids from games_results
        valid_game_ids = set()
        if table == 'player_stats' and 'game_id' in columns:
            # Ensure all game_ids are strings for comparison
            valid_game_ids = set(str(row[0]) for row in sqlite_conn.execute('SELECT game_id FROM games_results').fetchall())
            debug_msg = f"valid_game_ids length: {len(valid_game_ids)}\nSample valid_game_ids: {list(valid_game_ids)[:10]}\n"
            print(debug_msg)
            with open('valid_game_ids_debug.txt', 'w') as f:
                f.write(debug_msg)
        # Print debug info before the row loop
        if table == 'player_stats' and 'game_id' in columns:
            print(f"DEBUG: valid_game_ids length (pre-loop): {len(valid_game_ids)}")
            print(f"DEBUG: Sample valid_game_ids (pre-loop): {list(valid_game_ids)[:10]}")
        for row in rows:
            values = [convert_value(row[col]) for col in columns]
            # For player_stats, skip rows with missing or invalid game_id references BEFORE any other logic
            if table == 'player_stats' and 'game_id' in columns:
                game_id_idx = columns.index('game_id')
                game_id_val = values[game_id_idx]
                print(f"DEBUG: player_stats row game_id value: {game_id_val} (type: {type(game_id_val)})")
                # Skip if None or empty
                if game_id_val is None or str(game_id_val).strip() == '':
                    #print(f"Skipping player_stats row with empty game_id: {values}")
                    continue
                # Compare as string to avoid type mismatch
                if str(game_id_val) not in valid_game_ids:
                    #print(f"Skipping player_stats row with missing game_id: {values}")
                    continue
            # Special handling for boolean columns
            if table == 'players' and 'active' in columns:
                idx = columns.index('active')
                if values[idx] in (0, 1):
                    values[idx] = bool(values[idx])
            try:
                pg_cur.execute(insert_sql, values)
            except Exception as e:
                print(f"Error inserting into {table}: {e}\nRow: {values}")
    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    main()
