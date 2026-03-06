from sqlalchemy import update
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from zoneinfo import ZoneInfo
from backend.utils.redis_cache import redis_cache
from ..db import get_db
from ..services.aai.fresh_data_scraper import FreshDataScraper
from ..services.metrics import metrics_collector
from ..services.scraper_stats import PlayerStatsScraper
from ..services.espn_client import ESPNClient
from ..models.games_results import GameResult
from ..models.games_upcoming import GameUpcoming
from ..models.games_live import GameLive
from ..models.game import Game
from ..models.injury import Injury
from ..models.player import Player
from ..models.team import Team
from ..models.player_stats import PlayerStats
from ..models.bet import Bet

logger = logging.getLogger(__name__)

router = APIRouter(tags=["games"])
@router.post("/grade_completed_bets")

# ================= HELPERS =================
async def grade_completed_bets(session: AsyncSession = Depends(get_db)):
    """Grade all pending bets for games that are completed (status 'FT', 'completed', 'final')."""
    # Use final_keywords for robust status matching
    final_keywords = [
        "final",
        "ft",
        "full time",
        "full-time",
        "ended",
        "completed",
        "concluded",
        "game over",
        "postgame",
        "final/ot",
        "final/so",
        "final (ot)",
        "final (so)",
        "final (pen)",
        "final (agg)",
        "final (et)",
        "final (aet)",
        "final (pens)",
        "final (extra time)",
        "final (shootout)",
        "final (penalties)",
        "final (agg.)",
    ]
    # Fetch all games
    all_games_stmt = select(Game)
    all_games_result = await session.execute(all_games_stmt)
    all_games = list(all_games_result.scalars())
    completed_game_ids = [
        g.game_id for g in all_games
        if g.status and any(k in g.status.lower() for k in final_keywords)
    ]
    if not completed_game_ids:
        return {"graded": 0, "message": "No completed games found."}
    update_stmt = (
        update(Bet)
        .where(Bet.game_id.in_(completed_game_ids), Bet.status == "pending")
        .values(status="graded", graded_at=datetime.utcnow())
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(update_stmt)
    await session.commit()
    # Safely access rowcount, fallback to counting affected bets
    graded_count = getattr(result, "rowcount", None)
    if graded_count is None:
        # Fallback: count pending bets for completed games
        bet_count_stmt = select(Bet).where(Bet.game_id.in_(completed_game_ids), Bet.status == "graded")
        bet_count_result = await session.execute(bet_count_stmt)
        graded_count = len(list(bet_count_result.scalars()))
    return {"graded": graded_count, "message": f"Graded {graded_count} bets for completed games."}

def classify_game_status(
    status_detail: Optional[str],
    clock: Optional[str] = None,
    home_score: Optional[int] = None,
    away_score: Optional[int] = None,
) -> str:
    status_str = (status_detail or "").strip().lower()

    final_keywords = [
        "final",
        "ft",
        "full time",
        "full-time",
        "ended",
        "completed",
        "concluded",
        "game over",
        "postgame",
        "final/ot",
        "final/so",
        "final (ot)",
        "final (so)",
        "final (pen)",
        "final (agg)",
        "final (et)",
        "final (aet)",
        "final (pens)",
        "final (extra time)",
        "final (shootout)",
        "final (penalties)",
        "final (agg.)",
    ]
    live_keywords = [
        "in progress",
        "halftime",
        "half-time",
        "ht",
        "1st",
        "2nd",
        "3rd",
        "4th",
        "ot",
        "so",
        "et",
        "aet",
        "pens",
        "extra time",
        "shootout",
        "penalties",
        "quarter",
        "period",
        "inning",
        "top",
        "bottom",
        "kickoff",
        "pregame",
        "pre-game",
        "warmup",
        "delayed",
        "delay",
        "rain delay",
        "weather delay",
        "suspended",
        "paused",
        "break",
        "overtime",
        "live",
        "playing",
        "underway",
        "start of",
        "mid",
        "q1",
        "q2",
        "q3",
        "q4",
        "h1",
        "h2",
        "set",
        "match",
        "race",
        "lap",
        "minute",
        "min",
        "sec",
        "'",
    ]

    if any(k in status_str for k in final_keywords):
        return "completed"
    if any(k in status_str for k in live_keywords):
        return "ongoing"
    if (clock and str(clock).strip()) or ((home_score or 0) + (away_score or 0) > 0):
        return "ongoing"
    return "scheduled"


async def _build_ai_context(
    session: AsyncSession,
    *,
    pst_tz: ZoneInfo,
) -> Dict[str, object]:
    now_utc = datetime.utcnow().replace(microsecond=0)
    next_24h_utc = now_utc + timedelta(hours=24)
    logger.info(f"[AI] Filtering upcoming games: now_utc={now_utc}, next_24h_utc={next_24h_utc}")
    now_pst = datetime.now(pst_tz)
    today_pst = now_pst.date()
    yesterday_pst = today_pst - timedelta(days=1)

    # PST → UTC boundaries (naive UTC for DB)
    yesterday_start_pst = datetime.combine(
        yesterday_pst, datetime.min.time()
    ).replace(tzinfo=pst_tz)
    today_start_pst = datetime.combine(
        today_pst, datetime.min.time()
    ).replace(tzinfo=pst_tz)

    yesterday_start_utc = (
        yesterday_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    )
    today_start_utc = (
        today_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    )

    # ===== Yesterday's results =====
    yesterday_from_results = await session.execute(
        select(GameResult)
        .where(
            and_(
                GameResult.start_time >= yesterday_start_utc,
                GameResult.start_time < today_start_utc,
            )
        )
        .order_by(GameResult.start_time)
    )
    from typing import Union
    results: List[Union[GameResult, GameLive]] = list(yesterday_from_results.scalars().all())

    # Also include GameLive entries that are final and started yesterday
    all_live_result = await session.execute(select(GameLive))
    all_live_games: List[GameLive] = list(all_live_result.scalars().all())

    game_ids_in_results = {g.game_id for g in results if g.game_id}
    game_ids_to_lookup = [
        g.game_id
        for g in all_live_games
        if g.game_id and g.game_id not in game_ids_in_results
    ]

    upcoming_lookup: Dict[str, GameUpcoming] = {}
    game_lookup: Dict[str, Game] = {}

    if game_ids_to_lookup:
        import asyncio

        upcoming_result, game_result = await asyncio.gather(
            session.execute(
                select(GameUpcoming).where(
                    GameUpcoming.game_id.in_(game_ids_to_lookup)
                )
            ),
            session.execute(
                select(Game).where(Game.game_id.in_(game_ids_to_lookup))
            ),
            return_exceptions=False,
        )
        upcoming_lookup = {r.game_id: r for r in upcoming_result.scalars()}
        game_lookup = {g.game_id: g for g in game_result.scalars()}

    game_start_times: Dict[str, datetime] = {}

    for game_live in all_live_games:
        if game_live.game_id in game_ids_in_results:
            continue

        status_detail = game_live.status or ""
        if not (
            "final" in status_detail.lower()
            or "ft" in status_detail
            or status_detail == "Full Time"
        ):
            continue

        start_time: Optional[datetime] = None

        upcoming_record = upcoming_lookup.get(game_live.game_id)
        if upcoming_record and upcoming_record.start_time:
            start_time = upcoming_record.start_time

        if not start_time:
            game_record = game_lookup.get(game_live.game_id)
            if game_record and game_record.start_time:
                start_time = game_record.start_time

        if start_time:
            start_time_naive = (
                start_time.replace(tzinfo=None)
                if start_time.tzinfo
                else start_time
            )
            if yesterday_start_utc <= start_time_naive < today_start_utc:
                results.append(game_live)
                game_start_times[game_live.game_id] = start_time_naive

    def _sort_key(game_obj):
        if getattr(game_obj, "start_time", None):
            return game_obj.start_time
        if getattr(game_obj, "game_id", None) in game_start_times:
            return game_start_times[game_obj.game_id]
        return datetime.min

    results_sorted = sorted(results, key=_sort_key)

    # ===== Upcoming games (next 24h, scheduled only) =====
    now_utc = datetime.utcnow().replace(microsecond=0)
    next_24h_utc = now_utc + timedelta(hours=24)
    all_live_games_query = await session.execute(
        select(GameLive, Game.start_time)
        .join(Game, GameLive.game_id == Game.game_id)
        .order_by(Game.start_time.asc())
    )
    all_live_games_rows = all_live_games_query.all()

    upcoming: List[GameLive] = []
    for game_live, start_time in all_live_games_rows:
        if not start_time:
            #logger.info(f"[AI] Skipping game {getattr(game_live, 'game_id', None)}: no start_time")
            continue
        start_time_naive = start_time.replace(microsecond=0)
        if not (now_utc <= start_time_naive < next_24h_utc):
            #logger.info(f"[AI] Skipping game {getattr(game_live, 'game_id', None)}: start_time {start_time_naive} not in window {now_utc} - {next_24h_utc}")
            continue
        # Include all games in window, regardless of status
        upcoming.append(game_live)
        #logger.info(f"[AI] Including upcoming game {getattr(game_live, 'game_id', None)}: start_time {start_time_naive}, status {getattr(game_live, 'status', None)}")

    # ===== Build game/team mapping for injuries =====
    game_id_list = [g.game_id for g in upcoming if g.game_id]
    game_map: Dict[str, Dict[str, Optional[str]]] = {}
    team_ids: List[str] = []
    team_lookup: Dict[str, str] = {}
    team_id_by_name: Dict[str, str] = {}

    if game_id_list:
        upcoming_rows = await session.execute(
            select(GameUpcoming).where(GameUpcoming.game_id.in_(game_id_list))
        )
        upcoming_games = list(upcoming_rows.scalars().all())

        for game in upcoming_games:
            if not game.game_id:
                continue

            home_team_name = getattr(game, "home_team_name", None) or "Home"
            away_team_name = getattr(game, "away_team_name", None) or "Away"

            game_map[game.game_id] = {
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_team_name": home_team_name,
                "away_team_name": away_team_name,
            }

            if game.home_team_id:
                team_ids.append(game.home_team_id)
            if game.away_team_id:
                team_ids.append(game.away_team_id)

        missing_ids = [gid for gid in game_id_list if gid not in game_map]
        if missing_ids:
            game_rows = await session.execute(
                select(Game).where(Game.game_id.in_(missing_ids))
            )
            games = list(game_rows.scalars().all())
            for g in games:
                if not g.game_id:
                    continue
                game_map[g.game_id] = {
                    "home_team_id": g.home_team_id,
                    "away_team_id": g.away_team_id,
                    "home_team_name": g.home_team_name,
                    "away_team_name": g.away_team_name,
                }
                if g.home_team_id:
                    team_ids.append(g.home_team_id)
                if g.away_team_id:
                    team_ids.append(g.away_team_id)

    if upcoming:
        team_names = list(
            {
                name
                for g in upcoming
                for name in [g.home_team_name, g.away_team_name]
                if name
            }
        )
    else:
        team_names = []

    injuries_by_team: Dict[str, List[Dict[str, Optional[str]]]] = {}

    if team_ids or team_names:
        filter_clauses = []
        if team_ids:
            filter_clauses.append(Team.team_id.in_(team_ids))
        if team_names:
            filter_clauses.append(Team.name.in_(team_names))
            filter_clauses.append(Team.abbreviation.in_(team_names))

        team_rows = await session.execute(
            select(Team).where(or_(*filter_clauses))
        )
        teams = list(team_rows.scalars().all())

        for team in teams:
            if not team.team_id:
                continue
            team_ids.append(team.team_id)
            display_name = (
                team.name or team.abbreviation or team.team_id
            )
            team_lookup[team.team_id] = display_name
            if "-" in team.team_id:
                team_lookup[team.team_id.split("-")[-1]] = display_name
            if team.name:
                team_id_by_name[team.name] = team.team_id
            if team.abbreviation:
                team_id_by_name[team.abbreviation] = team.team_id

    if team_ids:
        injury_team_ids = set(team_ids)
        for tid in list(team_ids):
            if not tid:
                continue
            if "-" in tid:
                bare = tid.split("-")[-1]
                prefix = tid.split("-")[0]
                injury_team_ids.add(bare)
                injury_team_ids.add(f"{prefix}_{bare}")  # NBA-10 -> NBA_10 (injury table format)
            elif "_" in tid:
                prefix, bare = tid.split("_", 1)
                injury_team_ids.add(bare)
                injury_team_ids.add(f"{prefix}-{bare}")

        injuries_rows = await session.execute(
            select(Injury, Player)
            .outerjoin(Player, Injury.player_id == Player.player_id)
            .where(Injury.team_id.in_(list(injury_team_ids)))
            .order_by(Player.full_name)
        )

        for injury, player in injuries_rows.all():
            team_name = team_lookup.get(injury.team_id, injury.team_id)
            injuries_by_team.setdefault(injury.team_id, []).append(
                {
                    "team_name": team_name or injury.team_id,
                    "player_name": (
                        player.full_name or player.name
                        if player
                        else "Unknown"
                    ),
                    "status": injury.status or "Unknown",
                    "description": injury.description or "",
                    "last_updated": injury.last_updated.isoformat()
                    if injury.last_updated
                    else None,
                }
            )

    # Build name-based lookup as fallback for when team_ids are missing
    injuries_by_name: Dict[str, List] = {}
    for tid, inj_list in injuries_by_team.items():
        for inj in inj_list:
            tname = (inj.get("team_name") or "").strip().lower()
            if tname:
                injuries_by_name.setdefault(tname, [])
                # avoid dupes if multiple team_id keys map to same name
                existing_player_names = {i["player_name"] for i in injuries_by_name[tname]}
                for i in inj_list:
                    if i["player_name"] not in existing_player_names:
                        injuries_by_name[tname].append(i)
                        existing_player_names.add(i["player_name"])
                break  # one pass per tid is enough

    # ===== Format output =====
    output_lines: List[str] = []

    # Yesterday's results
    output_lines.append("=" * 60)
    output_lines.append(
        f"YESTERDAY'S RESULTS ({yesterday_pst.strftime('%Y-%m-%d')} PST)"
    )
    output_lines.append("=" * 60)
    output_lines.append("")

    if results_sorted:
        for result in results_sorted:
            sport = getattr(result, "sport", "Unknown Sport")
            away_name = getattr(result, "away_team_name", None) or "Away"
            home_name = getattr(result, "home_team_name", None) or "Home"
            away_score = getattr(result, "away_score", "N/A")
            home_score = getattr(result, "home_score", "N/A")

            output_lines.append(f"{sport}")
            output_lines.append(f"{away_name} @ {home_name}")
            output_lines.append(
                f"Final Score: {away_name} {away_score} - {home_score} {home_name}"
            )
            if getattr(result, "game_id", None):
                output_lines.append(f"Game ID: {result.game_id}")
            output_lines.append("")
    else:
        output_lines.append("No completed games found for yesterday.")
        output_lines.append("")

    # Today's upcoming games
    output_lines.append("=" * 60)
    output_lines.append("UPCOMING GAMES")
    output_lines.append("=" * 60)
    output_lines.append("")

    if upcoming:
        for gl in upcoming:
            sport = getattr(gl, "sport", "Unknown Sport")
            away_name = getattr(gl, "away_team_name", None) or "Away"
            home_name = getattr(gl, "home_team_name", None) or "Home"

            output_lines.append(f"{sport}")
            output_lines.append(f"{away_name} @ {home_name}")
            if getattr(gl, "game_id", None):
                output_lines.append(f"Game ID: {gl.game_id}")
            # Use start_time from joined Game object if available
            start_time = None
            if "start_time" in locals():
                start_time = start_time
            elif hasattr(gl, "start_time"):
                start_time = getattr(gl, "start_time", None)
            if start_time:
                try:
                    game_time_pst = (
                        start_time.replace(tzinfo=ZoneInfo("UTC"))
                        .astimezone(pst_tz)
                    )
                    output_lines.append(
                        f"Start Time: "
                        f"{game_time_pst.strftime('%I:%M %p PST')}"
                    )
                except Exception:
                    output_lines.append(
                        f"Start Time: {start_time}"
                    )
            if getattr(gl, "home_odds", None):
                away_odds = getattr(gl, "away_odds", "N/A")
                home_odds = getattr(gl, "home_odds", "N/A")
                output_lines.append(
                    f"Odds: {away_name} {away_odds} / {home_name} {home_odds}"
                )
            if getattr(gl, "home_record", None):
                away_record = getattr(gl, "away_record", "N/A")
                home_record = getattr(gl, "home_record", "N/A")
                output_lines.append(
                    f"Records: {away_name} ({away_record}) / "
                    f"{home_name} ({home_record})"
                )
            output_lines.append("")
    else:
        output_lines.append("No upcoming games found.")
        output_lines.append("")

    # Injuries for upcoming games
    output_lines.append("=" * 60)
    output_lines.append("INJURIES (LATEST SCRAPE)")
    output_lines.append("=" * 60)
    output_lines.append("")

    any_injuries = False
    if upcoming and injuries_by_team:
        for gl in upcoming:
            if not gl.game_id:
                continue

            meta = game_map.get(gl.game_id, {})
            home_name = (
                meta.get("home_team_name")
                or gl.home_team_name
                or "Home"
            )
            away_name = (
                meta.get("away_team_name")
                or gl.away_team_name
                or "Away"
            )
            home_team_id = meta.get("home_team_id") or team_id_by_name.get(
                home_name
            )
            away_team_id = meta.get("away_team_id") or team_id_by_name.get(
                away_name
            )

            home_key = home_team_id
            away_key = away_team_id

            def get_injuries_for_team(team_id, team_name=None):
                # Try ID-based lookup first
                if team_id:
                    for key in [
                        team_id,
                        team_id.replace("-", "_") if "-" in team_id else None,
                        team_id.replace("_", "-") if "_" in team_id else None,
                        team_id.split("-")[-1] if "-" in team_id else None,
                        team_id.split("_")[-1] if "_" in team_id else None,
                    ]:
                        if key and key in injuries_by_team:
                            return injuries_by_team[key]
                # Fall back to name-based lookup
                if team_name:
                    return injuries_by_name.get(team_name.strip().lower(), [])
                return []

            home_injuries = get_injuries_for_team(home_key, home_name)
            away_injuries = get_injuries_for_team(away_key, away_name)

            if not home_injuries and not away_injuries:
                continue

            any_injuries = True
            output_lines.append(f"{away_name} @ {home_name}")

            if home_injuries:
                output_lines.append(f"{home_name} Injuries:")
                for inj in home_injuries:
                    output_lines.append(
                        f"  - {inj['player_name']} ({inj['status']})"
                    )

            if away_injuries:
                output_lines.append(f"{away_name} Injuries:")
                for inj in away_injuries:
                    output_lines.append(
                        f"  - {inj['player_name']} ({inj['status']})"
                    )

            output_lines.append("")

    if not any_injuries:
        output_lines.append("No injuries listed for upcoming teams.")
        output_lines.append("")

    return {
        "text": "\n".join(output_lines),
        "yesterday_count": len(results_sorted),
        "today_count": len(upcoming),
    }


# ================= ROUTES =================


@router.get("/ai-context")
@redis_cache(ttl=60)
async def get_ai_context(session: AsyncSession = Depends(get_db)):
    """
    Get yesterday's results and today's upcoming games (plus injuries)
    formatted for AI consumption, using existing DB state.
    """
    logger.info("[AI-CONTEXT] Building AI context from cached data")
    pst = ZoneInfo("America/Los_Angeles")
    return await _build_ai_context(session, pst_tz=pst)


@router.get("/ai-context-fresh")
@redis_cache(ttl=60)
async def get_ai_context_fresh(session: AsyncSession = Depends(get_db)):
    """
    Scrape fresh data, then return the same AI context format.
    """
    logger.info("[AI-CONTEXT-FRESH] Starting fresh data scrape...")
    scraper = FreshDataScraper(session)
    summary: Dict[str, object] = {}
    try:
        summary = await scraper.scrape_all_fresh_data()
        logger.info("[AI-CONTEXT-FRESH] Fresh scrape summary: %s", summary)
    finally:
        await scraper.close()
        logger.info("[AI-CONTEXT-FRESH] FreshDataScraper closed")

    pst = ZoneInfo("America/Los_Angeles")
    context = await _build_ai_context(session, pst_tz=pst)
    context["fresh_data"] = summary
    return context


@router.get("/{game_id}/detailed")
async def get_game_details(
    game_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive game details including:
    - Game info and scores
    - Team stats and player stats
    - Bets on this game with live performance tracking
    - Box score and play-by-play data
    """
    game_result = await session.execute(
        select(Game)
        .where(Game.game_id == game_id)
        .options(
            selectinload(Game.home_team),
            selectinload(Game.away_team),
        )
    )
    game = game_result.scalar()

    if not game:
        return {"error": f"Game {game_id} not found"}

    game_live_result = await session.execute(
        select(GameLive).where(GameLive.game_id == game_id)
    )
    game_live = game_live_result.scalar()

    game_result_result = await session.execute(
        select(GameResult).where(GameResult.game_id == game_id)
    )
    game_result_obj = game_result_result.scalar()

    if game_result_obj:
        if (
            game_result_obj.home_score is not None
            and game_result_obj.away_score is not None
        ):
            current_status = "final"
        else:
            current_status = "live"
    elif game_live:
        status_str = (game_live.status or "").lower()
        if (
            any(
                word in status_str
                for word in [
                    "final",
                    "ft",
                    "full time",
                    "completed",
                    "complete",
                    "ended",
                ]
            )
            and game_live.home_score is not None
            and game_live.away_score is not None
        ):
            current_status = "final"
        else:
            current_status = "live"
    else:
        current_status = "upcoming"

    home_team = game.home_team
    away_team = game.away_team

    player_stats_result = await session.execute(
        select(PlayerStats)
        .where(PlayerStats.game_id == game_id)
        .options(selectinload(PlayerStats.player))
    )
    all_player_stats = list(player_stats_result.scalars().all())

    team_ids = {ps.team_id for ps in all_player_stats if ps.team_id}
    teams_result = await session.execute(
        select(Team).where(Team.team_id.in_(team_ids))
    )
    teams_by_id = {team.team_id: team for team in teams_result.scalars().all()}

    def get_team_name_from_id(team_id: Optional[str]) -> Optional[str]:
        if not team_id:
            return None
        team = teams_by_id.get(team_id)
        return team.name if team else None

    home_team_name = game.home_team_name or get_team_name_from_id(
        game.home_team_id
    )
    away_team_name = game.away_team_name or get_team_name_from_id(
        game.away_team_id
    )

    def matches_team_by_name(ps: PlayerStats, team_name: Optional[str]) -> bool:
        if not team_name or not ps.team_id:
            return False
        team_obj = teams_by_id.get(ps.team_id)
        ps_team_name = (
            team_obj.name.lower() if team_obj and team_obj.name else None
        )
        return ps_team_name == team_name.lower() if ps_team_name else False

    home_player_stats = [
        ps for ps in all_player_stats if matches_team_by_name(ps, home_team_name)
    ]
    away_player_stats = [
        ps for ps in all_player_stats if matches_team_by_name(ps, away_team_name)
    ]

    def calculate_team_stats(player_stats_list: List[PlayerStats]) -> Dict[str, int]:
        if not player_stats_list:
            return {}
        return {
            "points": sum(ps.points or 0 for ps in player_stats_list),
            "rebounds": sum(ps.rebounds or 0 for ps in player_stats_list),
            "assists": sum(ps.assists or 0 for ps in player_stats_list),
            "steals": sum(ps.steals or 0 for ps in player_stats_list),
            "blocks": sum(ps.blocks or 0 for ps in player_stats_list),
            "turnovers": sum(ps.turnovers or 0 for ps in player_stats_list),
            "player_count": len(player_stats_list),
        }

    home_team_stats = calculate_team_stats(home_player_stats)
    away_team_stats = calculate_team_stats(away_player_stats)

    bets_result = await session.execute(
        select(Bet)
        .where(Bet.game_id == game_id)
        .options(selectinload(Bet.player))
        .order_by(Bet.placed_at.desc())
    )
    bets = list(bets_result.scalars().all())

    enriched_bets: List[Dict[str, object]] = []
    for bet in bets:
        bet_data: Dict[str, object] = {
            "id": bet.id,
            "placed_at": bet.placed_at.isoformat() if bet.placed_at else None,
            "bet_type": bet.bet_type,
            "market": bet.market,
            "selection": bet.selection,
            "stat_type": bet.stat_type,
            "player_name": bet.player_name,
            "stake": bet.stake,
            "odds": bet.odds,
            "status": bet.status,
            "profit": bet.profit,
            "result_value": bet.result_value,
            "raw_text": bet.raw_text,
            "current_performance": None,
        }

        if bet.player_id and bet.player:
            player_stat = next(
                (ps for ps in all_player_stats if ps.player_id == bet.player_id),
                None,
            )
            stat_value: Optional[object] = None
            stat_display = None

            if player_stat and bet.stat_type:
                st = bet.stat_type.lower()
                if "points" in st or "pts" in st:
                    stat_value = player_stat.points
                    stat_display = f"{stat_value} PTS"
                elif "rebounds" in st or "reb" in st:
                    stat_value = player_stat.rebounds
                    stat_display = f"{stat_value} REB"
                elif "assists" in st or "ast" in st:
                    stat_value = player_stat.assists
                    stat_display = f"{stat_value} AST"
                elif "steals" in st or "stl" in st:
                    stat_value = player_stat.steals
                    stat_display = f"{stat_value} STL"
                elif "blocks" in st or "blk" in st:
                    stat_value = player_stat.blocks
                    stat_display = f"{stat_value} BLK"
                elif "3-pointers" in st or "3pt" in st:
                    stat_value = player_stat.three_pt
                    stat_display = f"{stat_value} 3PT"
                elif "passing yards" in st:
                    stat_value = player_stat.passing_yards
                    stat_display = f"{stat_value} YDS"
                elif "touchdowns" in st:
                    stat_value = (
                        player_stat.passing_tds or player_stat.receiving_tds
                    )
                    stat_display = f"{stat_value} TD"
                elif "rushing yards" in st:
                    stat_value = player_stat.rushing_yards
                    stat_display = f"{stat_value} YDS"

            bet_data["current_performance"] = {
                "player_id": bet.player_id,
                "player_name": bet.player.name
                or bet.player.full_name
                if bet.player
                else None,
                "stat_value": stat_value,
                "stat_display": stat_display,
                "team_id": player_stat.team_id if player_stat else None,
                "headshot": bet.player.headshot if bet.player else None,
                "jersey": bet.player.jersey if bet.player else None,
            }

        enriched_bets.append(bet_data)

    return {
        "game": {
            "game_id": game.game_id,
            "sport": game.sport,
            "league": game.league,
            "status": current_status,
            "start_time": game.start_time.isoformat()
            if game.start_time
            else None,
            "venue": game.venue,
            "home": {
                "team_id": game.home_team_id,
                "team_name": game.home_team_name,
                "logo": home_team.logo if home_team else None,
                "score": game.home_score,
                "stats": home_team_stats,
            },
            "away": {
                "team_id": game.away_team_id,
                "team_name": game.away_team_name,
                "logo": away_team.logo if away_team else None,
                "score": game.away_score,
                "stats": away_team_stats,
            },
            "period": game.period,
            "clock": game.clock,
            "boxscore_json": game.boxscore_json,
            "play_by_play_json": game.play_by_play_json,
        },
        "home_players": [
            {
                "player_id": ps.player_id,
                "player_name": ps.player.name
                or ps.player.full_name
                if ps.player
                else "Unknown",
                "jersey": ps.player.jersey if ps.player else None,
                "position": ps.player.position if ps.player else None,
                "headshot": ps.player.headshot if ps.player else None,
                "minutes": ps.minutes,
                "points": ps.points,
                "rebounds": ps.rebounds,
                "assists": ps.assists,
                "steals": ps.steals,
                "blocks": ps.blocks,
                "turnovers": ps.turnovers,
                "fg": ps.fg,
                "three_pt": ps.three_pt,
                "ft": ps.ft,
                "fouls": ps.fouls,
                "passing_yards": ps.passing_yards,
                "passing_tds": ps.passing_tds,
                "rushing_yards": ps.rushing_yards,
                "receiving_yards": ps.receiving_yards,
                "tackles": ps.tackles,
                "sacks": ps.sacks,
            }
            for ps in home_player_stats
        ],
        "away_players": [
            {
                "player_id": ps.player_id,
                "player_name": ps.player.name
                or ps.player.full_name
                if ps.player
                else "Unknown",
                "jersey": ps.player.jersey if ps.player else None,
                "position": ps.player.position if ps.player else None,
                "headshot": ps.player.headshot if ps.player else None,
                "minutes": ps.minutes,
                "points": ps.points,
                "rebounds": ps.rebounds,
                "assists": ps.assists,
                "steals": ps.steals,
                "blocks": ps.blocks,
                "turnovers": ps.turnovers,
                "fg": ps.fg,
                "three_pt": ps.three_pt,
                "ft": ps.ft,
                "fouls": ps.fouls,
                "passing_yards": ps.passing_yards,
                "passing_tds": ps.passing_tds,
                "rushing_yards": ps.rushing_yards,
                "receiving_yards": ps.receiving_yards,
                "tackles": ps.tackles,
                "sacks": ps.sacks,
            }
            for ps in away_player_stats
        ],
        "bets": enriched_bets,
        "total_bets": len(bets),
    }


@router.get("/metrics/scraper-performance")
@redis_cache(ttl=60)
async def get_scraper_metrics():
    """
    Get performance metrics for all scraping operations.
    """
    return {
        "summary": metrics_collector.get_summary(),
        "total_events": len(metrics_collector.events),
        "last_10_events": [
            {
                "operation": e.operation,
                "duration": f"{e.duration_seconds:.2f}s",
                "success": e.success,
                "error_type": e.error_type,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in metrics_collector.events[-10:]
        ],
    }


@router.post("/{game_id}/refresh-stats")
async def refresh_game_stats(
    game_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Manually refresh player stats for a specific game.
    Triggers immediate scrape of player statistics from ESPN.
    """
    client = ESPNClient()
    local_logger = logging.getLogger("refresh_game_stats")

    try:
        local_logger.info("[refresh_game_stats] Called for game_id=%s", game_id)

        game_result = await session.execute(
            select(Game).where(Game.game_id == game_id)
        )
        game = game_result.scalar()
        if not game:
            local_logger.error(
                "[refresh_game_stats] Game %s not found", game_id
            )
            return {"error": f"Game {game_id} not found", "success": False}

        sport_value = game.sport
        league_value = game.league

        sport_league_map = {
            "NBA": ("basketball", "nba"),
            "NCAAB": ("basketball", "mens-college-basketball"),
            "NFL": ("football", "nfl"),
            "NCAAF": ("football", "college-football"),
            "NHL": ("hockey", "nhl"),
            "EPL": ("soccer", "eng.1"),
            "MLB": ("baseball", "mlb"),
            "SOCCER": ("soccer", "eng.1"),
        }
        sport_upper = (sport_value or "").upper()
        if sport_upper not in sport_league_map:
            local_logger.error(
                "[refresh_game_stats] Unknown sport: %s", sport_value
            )
            return {
                "error": f"Unknown sport: {sport_value}",
                "success": False,
            }

        sport_type, league = sport_league_map[sport_upper]

        stats_scraper = PlayerStatsScraper(client)
        local_logger.info(
            "[refresh_game_stats] Scraping boxscore for game_id=%s, "
            "sport_type=%s, league=%s, sport_upper=%s",
            game_id,
            sport_type,
            league,
            sport_upper,
        )
        await stats_scraper._scrape_game_boxscore(
            session, game_id, sport_type, league, sport_upper
        )
        local_logger.info(
            "[refresh_game_stats] Successfully scraped stats for game_id=%s",
            game_id,
        )
        return {
            "success": True,
            "message": f"Player stats refreshed for game {game_id}",
            "game_id": game_id,
            "sport": sport_value,
            "league": league_value,
        }
    except Exception as exc:
        import traceback

        tb = traceback.format_exc()
        local_logger.error(
            "[refresh_game_stats] Exception for game_id=%s: %s\nTraceback:\n%s",
            game_id,
            exc,
            tb,
        )
        return {
            "success": False,
            "error": str(exc),
            "details": tb,
        }
    finally:
        await client.close()