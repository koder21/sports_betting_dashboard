#!/usr/bin/env python3
import asyncio
import re
import sqlite3
import sys
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "/Users/dakotanicol/sports_betting_dashboard")

from backend.services.espn_client import ESPNClient

SPORT_PATHS = {
    "nba": ("basketball", "nba"),
    "ncaab": ("basketball", "mens-college-basketball"),
    "soccer": ("soccer", "eng.1"),
}

TEAM_HINTS = {
    "nba": ["celtics", "heat", "bucks", "pacers", "timberwolves", "pelicans", "kings", "clippers"],
    "ncaab": ["uconn", "st. john"],
    "soccer": ["leeds", "nottingham"],
}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def detect_sport(game_text: str) -> str:
    lowered = game_text.lower()
    for sport, hints in TEAM_HINTS.items():
        if any(h in lowered for h in hints):
            return sport
    return "nba"


def parse_bets(text: str) -> List[Dict[str, str]]:
    bets = []
    blocks = re.split(r"(?=Type:)", text.strip())
    for block in blocks:
        if not block.strip():
            continue
        type_match = re.search(r"Type:\s*([^,]+)", block)
        selection_match = re.search(r"Selection:\s*([^,]+)", block)
        game_match = re.search(r"Game:\s*([^,]+)", block)
        date_match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", block)
        if not (type_match and selection_match and game_match and date_match):
            continue
        game_text = game_match.group(1).strip()
        bets.append(
            {
                "type": type_match.group(1).strip().lower(),
                "selection": selection_match.group(1).strip(),
                "game": game_text,
                "date": date_match.group(1).strip(),
                "sport": detect_sport(game_text),
            }
        )
    return bets


def team_score(team_query: str, team_obj: Dict) -> float:
    query = team_query.lower().strip()
    candidates = [
        team_obj.get("displayName", ""),
        team_obj.get("shortDisplayName", ""),
        team_obj.get("name", ""),
        team_obj.get("abbreviation", ""),
    ]
    best = 0.0
    for cand in candidates:
        cand_l = cand.lower().strip()
        if not cand_l:
            continue
        if query in cand_l or cand_l in query:
            best = max(best, 1.0)
        best = max(best, similarity(query, cand_l))
    return best


async def find_event_id(client: ESPNClient, sport: str, game_text: str, date_str: str) -> Optional[str]:
    sport_path = SPORT_PATHS.get(sport)
    if not sport_path:
        return None
    sport_name, league = sport_path
    date_compact = date_str.replace("-", "")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_name}/{league}/scoreboard?dates={date_compact}"
    data = await client.get_json(url)
    events = (data or {}).get("events", [])

    teams = [t.strip() for t in game_text.split(" vs ")]
    if len(teams) != 2:
        return None
    team1, team2 = teams

    best_match = None
    best_score = 0.0

    for event in events:
        comps = event.get("competitions", [])
        if not comps:
            continue
        competitors = comps[0].get("competitors", [])
        if len(competitors) < 2:
            continue
        c1 = competitors[0].get("team", {})
        c2 = competitors[1].get("team", {})
        score1 = team_score(team1, c1)
        score2 = team_score(team2, c2)
        score_alt1 = team_score(team1, c2)
        score_alt2 = team_score(team2, c1)

        pair_score = max(score1 + score2, score_alt1 + score_alt2)
        if pair_score > best_score:
            best_score = pair_score
            best_match = event

    if best_match and best_score >= 1.4:
        return best_match.get("id")
    return None


async def fetch_moneyline_odds(client: ESPNClient, sport: str, event_id: str, provider_id: int = 41) -> Optional[Dict[str, int]]:
    sport_path = SPORT_PATHS.get(sport)
    if not sport_path:
        return None
    sport_name, league = sport_path
    odds_url = f"https://sports.core.api.espn.com/v2/sports/{sport_name}/leagues/{league}/events/{event_id}/competitions/{event_id}/odds"
    odds_data = await client.get_json(odds_url)
    items = (odds_data or {}).get("items", [])
    for item in items:
        provider = (item.get("provider") or {}).get("id")
        if provider == provider_id:
            home_ml = (item.get("homeTeamOdds") or {}).get("moneyline")
            away_ml = (item.get("awayTeamOdds") or {}).get("moneyline")
            return {"home": home_ml, "away": away_ml}
    return None


async def backfill_bets(bet_text: str) -> None:
    bets = parse_bets(bet_text)
    if not bets:
        print("No bets parsed from text.")
        return

    conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
    cursor = conn.cursor()

    client = ESPNClient()
    try:
        for bet in bets:
            event_id = await find_event_id(client, bet["sport"], bet["game"], bet["date"])
            if not event_id:
                print(f"❌ No event found: {bet['game']} ({bet['date']})")
                continue

            cursor.execute(
                """
                UPDATE bets
                SET game_id = ?
                WHERE selection = ?
                """,
                (event_id, bet["selection"]),
            )

            if bet["type"] == "moneyline":
                odds = await fetch_moneyline_odds(client, bet["sport"], event_id)
                if odds:
                    cursor.execute(
                        """
                        UPDATE bets
                        SET odds = ?
                        WHERE selection = ?
                        """,
                        (odds.get("home") or odds.get("away") or -110, bet["selection"]),
                    )

            print(f"✅ Linked {bet['selection']} → {event_id}")

        conn.commit()
    finally:
        await client.close()
        conn.close()


if __name__ == "__main__":
    bet_text = """Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -150, Stake: 300, Reason: Matchup edge.
Type: moneyline, Selection: Bucks ML, Game: Bucks vs Pacers, Date: 2026-02-06, Odds: -140, Stake: 300, Reason: Efficiency advantage.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-06, Odds: -110, Stake: 300, Reason: High usage.
Type: moneyline, Selection: Kings ML, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -130, Stake: 250, Reason: Home edge.
Type: prop, Selection: De'Aaron Fox over 25.5 pts, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Favorable matchup.
Type: moneyline, Selection: UConn ML, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -180, Stake: 250, Reason: Power rating advantage.
Type: prop, Selection: Stephon Castle over 15.5 pts, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Usage projection.
Type: prop, Selection: Derrick White over 5.5 assists, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -110, Stake: 100, Reason: Increased playmaking role."""

    asyncio.run(backfill_bets(bet_text))
