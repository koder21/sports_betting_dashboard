import re
import psycopg2

# Map sport_name to ESPN logo URL pattern
ESPN_PATTERNS = {
    'NBA': 'https://a.espncdn.com/i/teamlogos/nba/500/{id}.png',
    'NHL': 'https://a.espncdn.com/i/teamlogos/nhl/500/{id}.png',
    'NFL': 'https://a.espncdn.com/i/teamlogos/nfl/500/{id}.png',
    'MLB': 'https://a.espncdn.com/i/teamlogos/mlb/500/{id}.png',
    'NCAAB': 'https://a.espncdn.com/i/teamlogos/ncaa/500/{id}.png',
    'NCAAF': 'https://a.espncdn.com/i/teamlogos/ncaa/500/{id}.png',
    'EPL': 'https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png',
    'SOCCER': 'https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png',
}

# Extract ESPN id from team_id or logo

def extract_espn_id(team_id, logo):
    # Try numeric id
    numeric = re.match(r'^(?:[A-Z]+-)?(\d+)$', team_id)
    if numeric:
        return numeric.group(1)
    # Try extracting from logo URL
    logo_id = re.search(r'/([\d]+)\.png', logo)
    if logo_id:
        return logo_id.group(1)
    # Try extracting from team_id suffix
    suffix = re.match(r'^[A-Z]+-(.+)$', team_id)
    if suffix:
        return suffix.group(1)
    return None

# Connect to DB
conn = psycopg2.connect(dbname='sports_intel', user='dakotanicol')
cursor = conn.cursor()


with open('scripts/logo_mismatches_audit.csv', 'r') as f:
    for line in f:
        # Skip header, separator, and empty lines
        if line.strip() == '' or line.startswith(' team_id') or set(line.strip()) <= {'-', '+', '|'}:
            continue
        # Split by pipe and strip whitespace
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4:
            continue
        team_id, name, sport_name, logo = parts[:4]
        sport_name = sport_name.upper()
        if sport_name in ESPN_PATTERNS:
            espn_id = extract_espn_id(team_id, logo)
            if espn_id:
                new_logo = ESPN_PATTERNS[sport_name].format(id=espn_id)
                cursor.execute(
                    "UPDATE teams SET logo = %s WHERE team_id = %s",
                    (new_logo, team_id)
                )
                print(f"Updated {team_id} ({sport_name}) to {new_logo}")

conn.commit()
cursor.close()
conn.close()
print("Batch logo update complete.")
