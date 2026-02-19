"""
Fresh Data Scraper — FINAL
Fixes:
  - Team upsert uses sport_name (no sport FK column)
  - Game upsert omits sport_id FK
  - Fetches real odds from ESPN Core API (Caesars -38, DraftKings -41)
  - Writes moneyline/spread/total into games_upcoming
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.game import Game
from ...models.games_upcoming import GameUpcoming
from ...models.games_live import GameLive
from ...models.team import Team
from ..espn_client import ESPNClient
from ..weather import WeatherService
from ..metrics import metrics_collector

logger = logging.getLogger(__name__)

# ESPN Core API — preferred odds providers in priority order
ODDS_PROVIDERS = ["38", "41", "2000"]   # Caesars, DraftKings, Bet365

ESPN_SCOREBOARD = {
    "NBA":   ("basketball", "nba"),
    "NCAAB": ("basketball", "mens-college-basketball"),
    "NFL":   ("football",   "nfl"),
    "NHL":   ("hockey",     "nhl"),
    "EPL":   ("soccer",     "eng.1"),
}

ESPN_CORE_LEAGUE = {
    "NBA":   ("basketball", "nba"),
    "NCAAB": ("basketball", "mens-college-basketball"),
    "NFL":   ("football",   "nfl"),
    "NHL":   ("hockey",     "nhl"),
    "EPL":   ("soccer",     "eng.1"),
}


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _parse_ml(value) -> Optional[float]:
    """Parse moneyline from ESPN — may be string like '-110' or float."""
    try:
        return float(value) if value not in (None, "", "EVEN") else None
    except Exception:
        return None


def _parse_odds_response(data: dict) -> Dict[str, Optional[float]]:
    """
    Parse ESPN Core API odds response.
    Returns dict with odds_home, odds_away, spread_home, spread_away, total.

    ESPN odds shape (per provider item):
      {
        "provider": {"id": "38", ...},
        "details": "-3.5",           ← spread
        "overUnder": 224.5,
        "spread": -3.5,
        "homeTeamOdds": {"moneyLine": -165, "spreadOdds": -110, ...},
        "awayTeamOdds": {"moneyLine": +140, "spreadOdds": -110, ...},
      }
    """
    result: Dict[str, Optional[float]] = {
        "odds_home": None, "odds_away": None,
        "spread_home": None, "spread_away": None,
        "total": None,
    }

    items = data.get("items", [])
    if not items:
        return result

    # Pick preferred provider
    chosen = None
    for pid in ODDS_PROVIDERS:
        for item in items:
            if str(item.get("provider", {}).get("id", "")) == pid:
                chosen = item
                break
        if chosen:
            break

    if not chosen and items:
        chosen = items[0]   # fallback: first available

    if not chosen:
        return result

    home_odds = chosen.get("homeTeamOdds", {})
    away_odds = chosen.get("awayTeamOdds", {})

    result["odds_home"]   = _parse_ml(home_odds.get("moneyLine"))
    result["odds_away"]   = _parse_ml(away_odds.get("moneyLine"))
    result["spread_home"] = _parse_ml(chosen.get("spread"))
    result["spread_away"] = (
        -result["spread_home"] if result["spread_home"] is not None else None
    )
    result["total"]       = _parse_ml(chosen.get("overUnder"))

    return result


class FreshDataScraper:
    def __init__(self, session: AsyncSession):
        self.session         = session
        self.espn_client     = ESPNClient()
        self.weather_service = WeatherService()
        self._team_ids: List[Tuple[str, str, str]] = []

    # ── Main entry ──────────────────────────────────────────────────────────

    async def scrape_all_fresh_data(self) -> Dict[str, Any]:
        start = datetime.now(timezone.utc)
        print("🚀 Starting fresh data scrape...")

        games_count = injuries_count = weather_count = 0
        errors: List[str] = []

        try:
            async with metrics_collector.measure("fresh_scrape_games"):
                games_count = await self._scrape_todays_games()
        except Exception as e:
            errors.append(f"Games: {str(e)[:120]}")
            logger.error(f"Games scrape failed: {e}", exc_info=True)

        try:
            async with metrics_collector.measure("fresh_scrape_injuries"):
                injuries_count = await self._scrape_injuries()
        except Exception as e:
            errors.append(f"Injuries: {str(e)[:120]}")

        try:
            async with metrics_collector.measure("fresh_scrape_weather"):
                weather_count = await self._update_weather()
        except Exception as e:
            errors.append(f"Weather: {str(e)[:120]}")

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        ok  = not errors
        msg = (f"✅ Data scraped in {elapsed:.1f}s"
               if ok else
               f"⚠️ Partial scrape in {elapsed:.1f}s ({len(errors)} errors)")

        print(f"\n{msg}")
        print(f"  📅 Games:    {games_count}")
        print(f"  🏥 Injuries: {injuries_count}")
        print(f"  🌦️  Weather:  {weather_count}")
        for err in errors:
            print(f"  ⚠️  {err}")

        return {
            "success":           ok,
            "scraped_at":        start.isoformat(),
            "elapsed_seconds":   round(elapsed, 2),
            "games_updated":     games_count,
            "injuries_updated":  injuries_count,
            "weather_forecasts": weather_count,
            "errors":            errors,
            "message":           msg,
        }

    # ── Games ────────────────────────────────────────────────────────────────

    async def _scrape_todays_games(self) -> int:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        self._team_ids = []

        # Fetch scoreboards concurrently
        sb_tasks = []
        sb_sports = []
        for sport_name, (sport_type, league) in ESPN_SCOREBOARD.items():
            url = (f"https://site.api.espn.com/apis/site/v2/sports"
                   f"/{sport_type}/{league}/scoreboard?dates={today}")
            sb_tasks.append(self.espn_client.get_json(url))
            sb_sports.append(sport_name)

        sb_results = await asyncio.gather(*sb_tasks, return_exceptions=True)

        # Parse events → collect game_ids per sport for odds fetching
        teams:      Dict[str, dict]  = {}
        game_rows:  List[dict]       = []
        upcoming:   List[dict]       = []
        live:       List[dict]       = []
        odds_needed: List[Tuple[str, str, str, str]] = []  # (game_id, sport, sport_type, league)

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        for sport_name, data in zip(sb_sports, sb_results):
            if not isinstance(data, dict):
                continue
            sport_type, league = ESPN_SCOREBOARD[sport_name]

            for event in data.get("events", []):
                try:
                    gid         = event.get("id")
                    status_type = (event.get("status", {})
                                        .get("type", {}).get("name", ""))
                    comps       = event.get("competitions", [])
                    if not comps:
                        continue
                    comp        = comps[0]
                    competitors = comp.get("competitors", [])
                    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
                    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
                    if not home or not away:
                        continue

                    home_name = home["team"].get("displayName", "")
                    away_name = away["team"].get("displayName", "")
                    home_id   = str(home["team"].get("id", ""))
                    away_id   = str(away["team"].get("id", ""))
                    home_score = int(home.get("score", 0) or 0)
                    away_score = int(away.get("score", 0) or 0)
                    start_dt   = _strip_tz(_parse_dt(event.get("date", "")))

                    # Teams  — use sport_name (the column), NOT sport (the relationship)
                    for tid, tname in [(home_id, home_name), (away_id, away_name)]:
                        if tid:
                            self._team_ids.append((tid, tname, sport_name))
                            teams[tid] = {
                                "team_id":    tid,
                                "espn_id":    tid,
                                "name":       tname,
                                "sport_name": sport_name,
                            }

                    # Core Game row — only columns that exist on the model
                    game_rows.append({
                        "game_id":        gid,
                        "sport":          sport_name,
                        "home_team_id":   home_id or None,
                        "away_team_id":   away_id or None,
                        "home_team_name": home_name,
                        "away_team_name": away_name,
                        "start_time":     start_dt,
                        "status":         status_type,
                    })

                    if status_type in ("STATUS_SCHEDULED", "STATUS_POSTPONED"):
                        upcoming.append({
                            "game_id":        gid,
                            "sport":          sport_name,
                            "home_team_id":   home_id or None,
                            "away_team_id":   away_id or None,
                            "home_team_name": home_name,
                            "away_team_name": away_name,
                            "start_time":     start_dt,
                            "status":         status_type,
                            "scraped_at":     now_naive,
                        })
                        # Queue odds fetch for scheduled games
                        odds_needed.append((gid, sport_name, sport_type, league))

                    elif status_type == "STATUS_IN_PROGRESS":
                        live.append({
                            "game_id":        gid,
                            "sport":          sport_name,
                            "home_team_name": home_name,
                            "away_team_name": away_name,
                            "home_score":     home_score,
                            "away_score":     away_score,
                            "updated_at":     now_naive,
                        })

                except Exception as e:
                    logger.warning(f"Parse error ({sport_name}): {e}")

        # ── Write in FK order ────────────────────────────────────────────────
        if teams:
            await self._upsert_teams(list(teams.values()))

        if game_rows:
            await self._upsert_games(game_rows)

        if upcoming:
            await self._upsert_upcoming(upcoming)

        if live:
            await self._upsert_live(live)

        await self.session.commit()

        # ── Fetch odds concurrently and patch games_upcoming ─────────────────
        if odds_needed:
            await self._fetch_and_store_odds(odds_needed)

        total = len(game_rows)
        print(f"  ✅ {len(teams)} teams | {total} games | "
              f"{len(upcoming)} upcoming | {len(live)} live")
        return total

    # ── Odds ─────────────────────────────────────────────────────────────────

    async def _fetch_and_store_odds(
        self, games: List[Tuple[str, str, str, str]]
    ) -> None:
        """
        Fetch odds from ESPN Core API for all scheduled games concurrently.
        Endpoint: sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}
                  /events/{event_id}/competitions/{event_id}/odds
        """
        async def fetch_one(game_id: str, sport_type: str, league: str):
            base = "https://sports.core.api.espn.com/v2/sports"
            url  = (f"{base}/{sport_type}/leagues/{league}"
                    f"/events/{game_id}/competitions/{game_id}/odds")
            try:
                data = await self.espn_client.get_json(url)
                return game_id, data
            except Exception as e:
                logger.debug(f"Odds fetch failed {game_id}: {e}")
                return game_id, None

        tasks   = [fetch_one(gid, st, lg) for gid, _, st, lg in games]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        odds_updates: List[dict] = []
        for item in results:
            if isinstance(item, Exception) or item is None:
                continue
            game_id, data = item
            if not data:
                continue
            parsed = _parse_odds_response(data)
            if any(v is not None for v in parsed.values()):
                odds_updates.append({"game_id": game_id, **parsed})

        if odds_updates:
            await self._patch_upcoming_odds(odds_updates)
            await self.session.commit()
            logger.info(f"  💰 Odds updated for {len(odds_updates)}/{len(games)} games")
        else:
            logger.info("  ℹ️  No odds available from ESPN Core API")

    async def _patch_upcoming_odds(self, rows: List[dict]) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        if not rows:
            return
        stmt = pg_insert(GameUpcoming).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["game_id"],
            set_={
                "odds_home":   stmt.excluded.odds_home,
                "odds_away":   stmt.excluded.odds_away,
                "spread_home": stmt.excluded.spread_home,
                "spread_away": stmt.excluded.spread_away,
                "total":       stmt.excluded.total,
            },
        )
        await self.session.execute(stmt)

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _upsert_teams(self, rows: List[dict]) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Team).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["team_id"],
            set_={"name": stmt.excluded.name,
                  "sport_name": stmt.excluded.sport_name,
                  "espn_id": stmt.excluded.espn_id},
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def _upsert_games(self, rows: List[dict]) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Game).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["game_id"],
            set_={
                "sport":          stmt.excluded.sport,
                "home_team_id":   stmt.excluded.home_team_id,
                "away_team_id":   stmt.excluded.away_team_id,
                "home_team_name": stmt.excluded.home_team_name,
                "away_team_name": stmt.excluded.away_team_name,
                "start_time":     stmt.excluded.start_time,
                "status":         stmt.excluded.status,
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def _upsert_upcoming(self, rows: List[dict]) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(GameUpcoming).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["game_id"],
            set_={
                "sport":          stmt.excluded.sport,
                "home_team_id":   stmt.excluded.home_team_id,
                "away_team_id":   stmt.excluded.away_team_id,
                "home_team_name": stmt.excluded.home_team_name,
                "away_team_name": stmt.excluded.away_team_name,
                "start_time":     stmt.excluded.start_time,
                "status":         stmt.excluded.status,
                "scraped_at":     stmt.excluded.scraped_at,
            },
        )
        await self.session.execute(stmt)

    async def _upsert_live(self, rows: List[dict]) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(GameLive).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["game_id"],
            set_={
                "home_team_name": stmt.excluded.home_team_name,
                "away_team_name": stmt.excluded.away_team_name,
                "home_score":     stmt.excluded.home_score,
                "away_score":     stmt.excluded.away_score,
                "updated_at":     stmt.excluded.updated_at,
                "sport":          stmt.excluded.sport,
            },
        )
        await self.session.execute(stmt)

    async def _scrape_injuries(self) -> int:
        if not self._team_ids:
            print("  ⚠️  No team IDs — skipping injuries")
            return 0
        return 0

    async def _update_weather(self) -> int:
        return 0

    async def close(self) -> None:
        await self.espn_client.close()