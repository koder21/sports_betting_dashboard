from typing import Any, Dict, List
from datetime import datetime

from .scraper_base import ScraperBase


class MLBScraper(ScraperBase):
    LEAGUE = "baseball/mlb"

    async def scrape(self) -> List[Dict[str, Any]]:
        url = f"{self.client.BASE}/{self.LEAGUE}/scoreboard"
        data = await self.client.get_json(url)
        if not data or "events" not in data:
            return []

        out = []
        for event in data["events"]:
            try:
                comp = event.get("competitions", [{}])[0]
                teams = comp.get("competitors", [])
                if len(teams) != 2:
                    continue

                home = next((t for t in teams if t.get("homeAway") == "home"), None)
                away = next((t for t in teams if t.get("homeAway") == "away"), None)
                if not home or not away:
                    continue

                out.append(
                    {
                        "espn_game_id": event.get("id"),
                        "start_time": datetime.fromisoformat(event["date"].replace("Z", "+00:00")),
                        "status": comp.get("status", {}).get("type", {}).get("name", "scheduled"),
                        "home_team": {
                            "espn_id": home.get("id"),
                            "name": home.get("team", {}).get("displayName"),
                            "abbrev": home.get("team", {}).get("abbreviation"),
                        },
                        "away_team": {
                            "espn_id": away.get("id"),
                            "name": away.get("team", {}).get("displayName"),
                            "abbrev": away.get("team", {}).get("abbreviation"),
                        },
                    }
                )
            except Exception:
                continue

        return out