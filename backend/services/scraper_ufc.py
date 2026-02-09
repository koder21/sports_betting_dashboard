from typing import Any, Dict, List
from datetime import datetime

from .scraper_base import ScraperBase


class UFCScraper(ScraperBase):
    LEAGUE = "mma/ufc"

    async def scrape(self) -> List[Dict[str, Any]]:
        url = f"{self.client.BASE}/{self.LEAGUE}/scoreboard"
        data = await self.client.get_json(url)
        if not data or "events" not in data:
            return []

        out = []
        for event in data["events"]:
            try:
                comp = event.get("competitions", [{}])[0]
                fighters = comp.get("competitors", [])
                if len(fighters) != 2:
                    continue

                red = fighters[0]
                blue = fighters[1]

                out.append(
                    {
                        "espn_event_id": event.get("id"),
                        "start_time": datetime.fromisoformat(event["date"].replace("Z", "+00:00")),
                        "status": comp.get("status", {}).get("type", {}).get("name", "scheduled"),
                        "fighter_red": {
                            "espn_id": red.get("id"),
                            "name": red.get("athlete", {}).get("displayName"),
                        },
                        "fighter_blue": {
                            "espn_id": blue.get("id"),
                            "name": blue.get("athlete", {}).get("displayName"),
                        },
                    }
                )
            except Exception:
                continue

        return out