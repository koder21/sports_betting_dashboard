#!/usr/bin/env python3
import asyncio
import re
import sys
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher

sys.path.insert(0, "/Users/dakotanicol/sports_betting_dashboard")

from backend.services.espn_client import ESPNClient
from scripts.upsert_games_from_espn import SPORT_PATHS

STAT_MAP = {
    "pts": "points",
    "points": "points",
    "ast": "assists",
    "assists": "assists",
    "reb": "rebounds",
    "rebounds": "rebounds",
    "stl": "steals",
    "steals": "steals",
    "blk": "blocks",
    "blocks": "blocks",
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", name.lower()).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def parse_prop(selection: str):
    sel = selection.lower().strip()
    over_under = "over" if " over " in f" {sel} " else "under"
    # extract line number
    num_match = re.search(r"(\d+\.?\d*)", sel)
    line = float(num_match.group(1)) if num_match else None
    # stat key is last token
    stat_token = sel.split()[-1]
    stat_key = STAT_MAP.get(stat_token, None)
    # player name is before over/under
    name_part = sel.split(" over ")[0] if " over " in sel else sel.split(" under ")[0]
    player_name = name_part.strip()
    return player_name, over_under, line, stat_key


def calc_profit(stake: float, odds: float, won: bool) -> float:
    if not won:
        return -stake
    if odds > 0:
        return stake * (odds / 100)
    return stake / (abs(odds) / 100)


async def get_player_stat(client: ESPNClient, sport: str, league_code: str, event_id: str, player_name: str, stat_key: str):
    path = SPORT_PATHS.get(sport)
    if not path:
        return None
    if sport == "soccer":
        path = f"soccer/{league_code}"

    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={event_id}"
    data = await client.get_json(summary_url)
    players = (data or {}).get("boxscore", {}).get("players", [])

    best_match = None
    best_score = 0.0
    player_norm = normalize_name(player_name)
    player_last = player_norm.split()[-1] if player_norm else ""

    for team in players:
        for stat_group in team.get("statistics", []):
            keys = stat_group.get("keys", [])
            athletes = stat_group.get("athletes", [])
            if stat_key not in keys:
                continue
            stat_index = keys.index(stat_key)
            for athlete in athletes:
                stats_list = athlete.get("stats", [])
                if stat_index >= len(stats_list):
                    continue
                athlete_name = (athlete.get("athlete", {}) or {}).get("displayName", "")
                athlete_norm = normalize_name(athlete_name)
                score = similarity(player_norm, athlete_norm)
                if player_last and player_last in athlete_norm:
                    score = max(score, 0.9)
                if score > best_score:
                    best_score = score
                    best_match = (athlete_name, stats_list[stat_index])

    if best_match and best_score >= 0.65:
        return best_match
    return None


async def run():
    conn = sqlite3.connect("/Users/dakotanicol/sports_betting_dashboard/sports_intel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT b.id, b.selection, b.odds, b.stake, b.game_id, s.name, s.espn_league_code
        FROM bets b
        LEFT JOIN sports s ON s.id = b.sport_id
        WHERE b.status = 'pending' AND b.bet_type = 'prop'
        """
    )
    bets = cursor.fetchall()

    if not bets:
        print("No pending prop bets.")
        conn.close()
        return

    client = ESPNClient()
    try:
        for bet_id, selection, odds, stake, game_id, sport, league_code in bets:
            player_name, over_under, line, stat_key = parse_prop(selection)
            if not (player_name and line is not None and stat_key and game_id and sport):
                print(f"❌ Skipping bet {bet_id} (unable to parse)")
                continue

            result = await get_player_stat(client, sport, league_code, game_id, player_name, stat_key)
            if not result:
                cursor.execute(
                    """
                    UPDATE bets
                    SET status = ?, graded_at = ?, result_value = ?, profit = ?
                    WHERE id = ?
                    """,
                    ("void", datetime.utcnow().isoformat(), None, 0, bet_id),
                )
                print(f"⚠️  Bet {bet_id} {selection} → void (no stats found)")
                continue

            matched_name, value = result
            try:
                value = float(value)
            except Exception:
                print(f"❌ Invalid stat value for {selection}")
                continue

            won = value > line if over_under == "over" else value < line
            status = "won" if won else "lost"
            profit = calc_profit(stake, odds, won)

            cursor.execute(
                """
                UPDATE bets
                SET status = ?, profit = ?, graded_at = ?, result_value = ?
                WHERE id = ?
                """,
                (status, profit, datetime.utcnow().isoformat(), value, bet_id),
            )

            print(f"✅ Bet {bet_id} {selection} → {status} ({matched_name}: {value})")

        conn.commit()
    finally:
        await client.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(run())
