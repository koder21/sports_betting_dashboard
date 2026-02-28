"""
link_bets_to_games.py

Links unpaired bets from raw text to ESPN game IDs and updates the database.
"""

import asyncio
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path("/Users/dakotanicol/sports_betting_dashboard")
DB_PATH = PROJECT_ROOT / "sports_intel.db"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.espn_client import ESPNClient  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_ODDS = -110
SIMILARITY_THRESHOLD = 0.70

SPORT_KEYWORDS: dict[str, list[str]] = {
    "nba": [
        "celtics", "heat", "bucks", "pacers", "timberwolves",
        "pelicans", "kings", "clippers", "lakers", "nets",
    ],
    "college-basketball": [
        "uconn", "st. john's", "duke", "kansas", "kentucky",
    ],
    "soccer": [
        "leeds", "nottingham", "arsenal", "man city", "liverpool",
        "chelsea", "tottenham",
    ],
    "nfl": [
        "chiefs", "patriots", "cowboys", "packers", "eagles",
    ],
}


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class Bet:
    type: str
    selection: str
    game: str
    date: str
    stake: int
    sport: str
    odds: int = DEFAULT_ODDS
    reason: str = ""
    game_id: Optional[str] = None

    @property
    def game_key(self) -> tuple[str, str, str]:
        return (self.sport, self.game, self.date)

    @property
    def teams(self) -> Optional[tuple[str, str]]:
        parts = [t.strip() for t in self.game.split(" vs ")]
        return (parts[0], parts[1]) if len(parts) == 2 else None


# ── Sport detection ───────────────────────────────────────────────────────────
def detect_sport(game_info: str) -> str:
    """Infer sport from team names in game_info. Defaults to 'nba'."""
    lower = game_info.lower()
    for sport, keywords in SPORT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return sport
    return "nba"


# ── Parsing ───────────────────────────────────────────────────────────────────
_FIELD_PATTERNS: dict[str, re.Pattern] = {
    "type":      re.compile(r"Type:\s*(\w+)", re.I),
    "selection": re.compile(r"Selection:\s*([^,]+)", re.I),
    "game":      re.compile(r"Game:\s*([^,]+)", re.I),
    "date":      re.compile(r"Date:\s*(\d{4}-\d{2}-\d{2})", re.I),
    "odds":      re.compile(r"Odds:\s*([-+]?\d+)", re.I),
    "stake":     re.compile(r"Stake:\s*(\d+)", re.I),
    "reason":    re.compile(r"Reason:\s*([^.\n]+)", re.I),
}

REQUIRED_FIELDS = {"type", "selection", "game", "date", "stake"}


def parse_bets(text: str) -> list[Bet]:
    """Parse one or more bets from raw text blocks."""
    bets: list[Bet] = []
    blocks = re.split(r"(?=Type:)", text.strip())

    for block in filter(str.strip, blocks):
        raw: dict[str, str] = {}
        for key, pattern in _FIELD_PATTERNS.items():
            m = pattern.search(block)
            if m:
                raw[key] = m.group(1).strip()

        missing = REQUIRED_FIELDS - raw.keys()
        if missing:
            log.warning("Skipping block — missing fields %s:\n  %s", missing, block[:80])
            continue

        game = raw["game"]
        bets.append(
            Bet(
                type=raw["type"].lower(),
                selection=raw["selection"],
                game=game,
                date=raw["date"],
                stake=int(raw["stake"]),
                odds=int(raw.get("odds", DEFAULT_ODDS)),
                reason=raw.get("reason", ""),
                sport=detect_sport(game),
            )
        )

    return bets


# ── ESPN lookup ───────────────────────────────────────────────────────────────
def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


async def _fetch_games(client: ESPNClient, sport: str, date: str) -> list[dict]:
    """Call whichever fetch method the client exposes."""
    for method_name in ("fetch_games", "get_games"):
        method = getattr(client, method_name, None)
        if method:
            return await method(sport, date) or []
    raise AttributeError(
        f"ESPNClient has neither 'fetch_games' nor 'get_games'. "
        f"Available: {[m for m in dir(client) if not m.startswith('_')]}"
    )


async def find_game(sport: str, team1: str, team2: str, date: str) -> Optional[dict]:
    """Return the ESPN game dict matching the two teams on a given date."""
    client = ESPNClient()
    games = await _fetch_games(client, sport, date)

    t1, t2 = team1.lower().strip(), team2.lower().strip()

    for game in games:
        home = game.get("home_team", "").lower().strip()
        away = game.get("away_team", "").lower().strip()

        home_t1 = _similarity(t1, home) > SIMILARITY_THRESHOLD
        away_t2 = _similarity(t2, away) > SIMILARITY_THRESHOLD
        home_t2 = _similarity(t2, home) > SIMILARITY_THRESHOLD
        away_t1 = _similarity(t1, away) > SIMILARITY_THRESHOLD

        if (home_t1 and away_t2) or (home_t2 and away_t1):
            return game

    return None


# ── Database ──────────────────────────────────────────────────────────────────
_UPDATE_SQL = """
    UPDATE bets
    SET    game_id = ?
    WHERE  game_id IS NULL
      AND  DATE(placed_at) = ?
      AND  (
               LOWER(raw_text)  LIKE LOWER(?)
            OR LOWER(selection) LIKE LOWER(?)
           )
"""


def update_bets_in_db(
    cursor: sqlite3.Cursor,
    game_id: str,
    date: str,
    team1: str,
    selection: str,
) -> int:
    """Attach a game_id to matching unlinked rows. Returns the number updated."""
    cursor.execute(_UPDATE_SQL, (game_id, date, f"%{team1}%", f"%{selection}%"))
    return cursor.rowcount


# ── Orchestration ─────────────────────────────────────────────────────────────
async def link_bets_to_games(bet_text: str) -> None:
    """Parse bets, resolve ESPN game IDs, and persist to the database."""
    bets = parse_bets(bet_text)
    if not bets:
        log.error("No valid bets found in input.")
        return

    log.info("Parsed %d bet(s) from text.", len(bets))

    # Group by unique game so we only hit ESPN once per game
    games_to_bets: dict[tuple, list[Bet]] = {}
    for bet in bets:
        games_to_bets.setdefault(bet.game_key, []).append(bet)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_updated = 0

    try:
        for (sport, game_info, date), group in games_to_bets.items():
            log.info("Searching ESPN — %s: %s (%s)", sport.upper(), game_info, date)

            bet = group[0]  # representative bet; all share the same game
            teams = bet.teams
            if teams is None:
                log.warning("  Could not parse teams from '%s' — skipping.", game_info)
                continue

            team1, team2 = teams
            game = await find_game(sport, team1, team2, date)

            if game is None:
                log.warning("  No ESPN match found for %s vs %s.", team1, team2)
                continue

            game_id = str(game["id"])
            log.info(
                "  Matched: %s @ %s  (id=%s)",
                game["away_team"],
                game["home_team"],
                game_id,
            )

            updated = 0
            for b in group:
                updated += update_bets_in_db(cursor, game_id, date, team1, b.selection)

            conn.commit()
            total_updated += updated
            log.info("  Updated %d row(s) in the database.", updated)

    finally:
        conn.close()

    log.info("Done. %d total bet row(s) linked to games.", total_updated)


# ── Entry point ───────────────────────────────────────────────────────────────
SAMPLE_BETS = """\
Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -150, Stake: 300, Reason: Matchup edge.
Type: moneyline, Selection: Bucks ML, Game: Bucks vs Pacers, Date: 2026-02-06, Odds: -140, Stake: 300, Reason: Efficiency advantage.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-06, Odds: -110, Stake: 300, Reason: High usage.
Type: moneyline, Selection: Kings ML, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -130, Stake: 250, Reason: Home edge.
Type: prop, Selection: De'Aaron Fox over 25.5 pts, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Favorable matchup.
Type: moneyline, Selection: UConn ML, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -180, Stake: 250, Reason: Power rating advantage.
Type: prop, Selection: Stephon Castle over 15.5 pts, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Usage projection.
Type: moneyline, Selection: Leeds ML, Game: Leeds vs Nottingham Forest, Date: 2026-02-06, Odds: -120, Stake: 100, Reason: Home form advantage.
Type: prop, Selection: Derrick White over 5.5 assists, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -110, Stake: 100, Reason: Increased playmaking role.
"""

if __name__ == "__main__":
    asyncio.run(link_bets_to_games(SAMPLE_BETS))