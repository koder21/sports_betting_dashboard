#!/usr/bin/env python3
import asyncio
import sys
import sqlite3
from typing import Optional

sys.path.insert(0, "/Users/dakotanicol/sports_betting_dashboard")

from backend.services.espn_client import ESPNClient

SPORT_PATHS = {
    "nba": "basketball/nba",
    "nfl": "football/nfl",
    "nhl": "hockey/nhl",
    "mlb": "baseball/mlb",
    "ufc": "mma/ufc",
    "ncaaf": "football/college-football",
    "ncaab": "basketball/mens-college-basketball",
    "soccer": "soccer",  # requires league code
}


def normalize_status(status_obj: dict) -> str:
    status_type = (status_obj or {}).get("type", {})
    if status_type.get("completed"):
        return "final"
    name = (status_type.get("name") or "").lower()
    state = (status_type.get("state") or "").lower()
    if "final" in name or "post" in state:
        return "final"
    if "in" in state or "live" in name:
        return "live"
    return (status_type.get("name") or "scheduled").lower() or "scheduled"


async def upsert_game_from_event(client: ESPNClient, event_id: str, sport: str, league_code: Optional[str]) -> Optional[dict]:
    path = SPORT_PATHS.get(sport)
    if not path:
        return None
    if sport == "soccer" and league_code:
        path = f"soccer/{league_code}"

    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={event_id}"
    data = await client.get_json(summary_url)
    comps = (data or {}).get("header", {}).get("competitions", [])
    if not comps:
        return None

    comp = comps[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[-1])

    game = {
        "game_id": event_id,
        "sport": sport,
        "league": league_code,
        "start_time": comp.get("date"),
        "status": normalize_status(comp.get("status", {})),
        "home_team_name": (home.get("team") or {}).get("displayName"),
        "away_team_name": (away.get("team") or {}).get("displayName"),
        "home_score": int(home.get("score")) if home.get("score") is not None else None,
        "away_score": int(away.get("score")) if away.get("score") is not None else None,
        "period": (comp.get("status") or {}).get("period"),
        "clock": (comp.get("status") or {}).get("displayClock"),
    }
    return game


async def run() -> None:
    conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT b.game_id, s.name, s.espn_league_code
        FROM bets b
        LEFT JOIN sports s ON s.id = b.sport_id
        WHERE b.game_id IS NOT NULL
        """
    )
    rows = cursor.fetchall()

    if not rows:
        print("No bets with game_id found.")
        conn.close()
        return

    client = ESPNClient()
    try:
        for game_id, sport, league_code in rows:
            if not sport:
                continue
            game = await upsert_game_from_event(client, game_id, sport, league_code)
            if not game:
                print(f"❌ Could not fetch event {game_id} ({sport})")
                continue

            cursor.execute(
                """
                INSERT INTO games (game_id, sport, league, start_time, status, home_team_name, away_team_name, home_score, away_score, period, clock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    sport=excluded.sport,
                    league=excluded.league,
                    start_time=excluded.start_time,
                    status=excluded.status,
                    home_team_name=excluded.home_team_name,
                    away_team_name=excluded.away_team_name,
                    home_score=excluded.home_score,
                    away_score=excluded.away_score,
                    period=excluded.period,
                    clock=excluded.clock
                """,
                (
                    game["game_id"],
                    game["sport"],
                    game["league"],
                    game["start_time"],
                    game["status"],
                    game["home_team_name"],
                    game["away_team_name"],
                    game["home_score"],
                    game["away_score"],
                    game["period"],
                    game["clock"],
                ),
            )

            print(
                f"✅ Upserted {game['away_team_name']} @ {game['home_team_name']} "
                f"({game['status']}) {game['away_score']}-{game['home_score']}"
            )

        conn.commit()
    finally:
        await client.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(run())
