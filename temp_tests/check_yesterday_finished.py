import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Get the data from stdin
data = json.load(sys.stdin)

# PST timezone boundaries for yesterday
pst = ZoneInfo("America/Los_Angeles")
yesterday_start_pst = datetime(2026, 2, 9, 0, 0, 0, tzinfo=pst)
yesterday_end_pst = datetime(2026, 2, 10, 0, 0, 0, tzinfo=pst)

# Convert to UTC
yesterday_start_utc = yesterday_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
yesterday_end_utc = yesterday_end_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

print(f"Yesterday PST: {yesterday_start_pst.date()} to {yesterday_end_pst.date()}")
print(f"Yesterday UTC: {yesterday_start_utc} to {yesterday_end_utc}")
print()

count = 0
games_yesterday = []

for game in data:
    if game.get("status") != "final":
        continue
    
    start_time_str = game.get("start_time", "")
    if not start_time_str:
        continue
    
    # Parse the timestamp
    try:
        if start_time_str.endswith("Z"):
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        else:
            start_time = datetime.fromisoformat(start_time_str)
        
        # Remove timezone info for comparison
        if start_time.tzinfo:
            start_time = start_time.replace(tzinfo=None)
        
        # Check if in yesterday's range
        if yesterday_start_utc <= start_time < yesterday_end_utc:
            count += 1
            games_yesterday.append({
                "game_id": game.get("game_id"),
                "matchup": f"{game.get('away_team', 'Away')} @ {game.get('home_team', 'Home')}",
                "start_time": start_time
            })
    except Exception as e:
        pass

print(f"Finished games from yesterday (02/09/2026): {count}")
print()
for game in sorted(games_yesterday, key=lambda x: x["start_time"]):
    print(f"  {game['matchup']} | {game['start_time']}")
