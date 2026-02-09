from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict
from zoneinfo import ZoneInfo

from ..db import get_session
from ..services.intelligence.game_intel import GameIntelligenceService
from ..models.games_results import GameResult
from ..models.games_upcoming import GameUpcoming
from ..models.games_live import GameLive
from ..models.game import Game
from ..models.injury import Injury
from ..models.player import Player
from ..models.team import Team

router = APIRouter()


@router.get("/ai-context")
async def get_ai_context(session: AsyncSession = Depends(get_session)):
    """Get yesterday's results and today's upcoming games for AI analysis"""
    # Use PST timezone for date calculations
    pst = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst)
    today_pst = now_pst.date()
    yesterday_pst = today_pst - timedelta(days=1)
    
    # Convert PST dates to UTC for database queries
    yesterday_start_pst = datetime.combine(yesterday_pst, datetime.min.time()).replace(tzinfo=pst)
    today_start_pst = datetime.combine(today_pst, datetime.min.time()).replace(tzinfo=pst)
    
    # Convert to UTC for database comparison (assuming DB stores in UTC)
    yesterday_start_utc = yesterday_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    today_start_utc = today_start_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    
    # Get yesterday's results (games that started during yesterday PST)
    yesterday_results = await session.execute(
        select(GameResult)
        .where(
            and_(
                GameResult.start_time >= yesterday_start_utc,
                GameResult.start_time < today_start_utc,
                or_(
                    GameResult.status == "STATUS_FINAL",
                    GameResult.status == "Final",
                    GameResult.status.like("%Final%")
                )
            )
        )
        .order_by(GameResult.start_time)
    )
    results = yesterday_results.scalars().all()
    
    # Get ALL games from GameLive (same as /live endpoint does)
    # The /live endpoint filters status in Python code, so we'll get everything
    today_upcoming_query = await session.execute(select(GameLive))
    all_live_games = today_upcoming_query.scalars().all()
    
    # Filter for upcoming games (not final) in Python
    upcoming = [
        game for game in all_live_games 
        if game.status and "Final" not in game.status and "FT" not in game.status
    ]
    
    # Build game/team mapping for injuries (no re-scrape, DB only)
    game_id_list = [game.game_id for game in upcoming if game.game_id]
    game_map: Dict[str, Dict[str, str]] = {}
    team_ids: List[str] = []
    team_lookup: Dict[str, str] = {}
    team_id_by_name: Dict[str, str] = {}
    if game_id_list:
        upcoming_rows = await session.execute(
            select(GameUpcoming).where(GameUpcoming.game_id.in_(game_id_list))
        )
        upcoming_games = upcoming_rows.scalars().all()
        for game in upcoming_games:
            if not game.game_id:
                continue
            game_map[game.game_id] = {
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_team_name": game.home_team_name,
                "away_team_name": game.away_team_name,
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
            games = game_rows.scalars().all()
            for game in games:
                if not game.game_id:
                    continue
                game_map[game.game_id] = {
                    "home_team_id": game.home_team_id,
                    "away_team_id": game.away_team_id,
                    "home_team_name": game.home_team_name,
                    "away_team_name": game.away_team_name,
                }
                if game.home_team_id:
                    team_ids.append(game.home_team_id)
                if game.away_team_id:
                    team_ids.append(game.away_team_id)

    injuries_by_team: Dict[str, List[Dict[str, str]]] = {}
    if upcoming:
        team_names = list({
            name for game in upcoming
            for name in [game.home_team_name, game.away_team_name]
            if name
        })
    else:
        team_names = []

    if team_ids or team_names:
        team_rows = await session.execute(
            select(Team).where(
                or_(
                    Team.team_id.in_(team_ids) if team_ids else False,
                    Team.name.in_(team_names) if team_names else False,
                    Team.abbreviation.in_(team_names) if team_names else False,
                )
            )
        )
        teams = team_rows.scalars().all()
        for team in teams:
            if team.team_id:
                team_ids.append(team.team_id)
                team_lookup[team.team_id] = team.name or team.abbreviation or team.team_id
                if "-" in team.team_id:
                    team_lookup[team.team_id.split("-")[-1]] = team_lookup[team.team_id]
                if team.name:
                    team_id_by_name[team.name] = team.team_id
                if team.abbreviation:
                    team_id_by_name[team.abbreviation] = team.team_id

    if team_ids:
        injury_team_ids = set(team_ids)
        for team_id in list(team_ids):
            if team_id and "-" in team_id:
                injury_team_ids.add(team_id.split("-")[-1])

        injuries_rows = await session.execute(
            select(Injury, Player)
            .outerjoin(Player, Injury.player_id == Player.player_id)
            .where(Injury.team_id.in_(list(injury_team_ids)))
            .order_by(Player.full_name)
        )
        for injury, player in injuries_rows.all():
            team_name = team_lookup.get(injury.team_id, injury.team_id)
            injuries_by_team.setdefault(injury.team_id, []).append({
                "team_name": team_name or injury.team_id,
                "player_name": (player.full_name or player.name) if player else "Unknown",
                "status": injury.status or "Unknown",
                "description": injury.description or "",
                "last_updated": injury.last_updated.isoformat() if injury.last_updated else None,
            })

    # Format the output for AI
    output_lines = []
    
    # Yesterday's results
    output_lines.append("=" * 60)
    output_lines.append(f"YESTERDAY'S RESULTS ({yesterday_pst.strftime('%Y-%m-%d')} PST)")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    if results:
        for game in results:
            output_lines.append(f"{game.sport}")
            output_lines.append(f"{game.away_team_name} @ {game.home_team_name}")
            output_lines.append(f"Final Score: {game.away_team_name} {game.away_score} - {game.home_score} {game.home_team_name}")
            if game.game_id:
                output_lines.append(f"Game ID: {game.game_id}")
            output_lines.append("")
    else:
        output_lines.append("No completed games found for yesterday.")
        output_lines.append("")
    
    # Today's upcoming games
    output_lines.append("=" * 60)
    output_lines.append(f"UPCOMING GAMES")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    if upcoming:
        for game in upcoming:
            output_lines.append(f"{game.sport or 'Unknown Sport'}")
            output_lines.append(f"{game.away_team_name or 'Away'} @ {game.home_team_name or 'Home'}")
            if game.game_id:
                output_lines.append(f"Game ID: {game.game_id}")
            if hasattr(game, 'start_time') and game.start_time:
                # Convert UTC time to PST for display
                try:
                    game_time_pst = game.start_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(pst)
                    output_lines.append(f"Start Time: {game_time_pst.strftime('%I:%M %p PST')}")
                except:
                    output_lines.append(f"Start Time: {game.start_time}")
            if hasattr(game, 'home_odds') and game.home_odds:
                output_lines.append(f"Odds: {game.away_team_name or 'Away'} {game.away_odds} / {game.home_team_name or 'Home'} {game.home_odds}")
            if hasattr(game, 'home_record') and game.home_record:
                output_lines.append(f"Records: {game.away_team_name or 'Away'} ({game.away_record}) / {game.home_team_name or 'Home'} ({game.home_record})")
            output_lines.append("")
    else:
        output_lines.append("No upcoming games found.")
        output_lines.append("")

    # Injuries for upcoming games (from latest scrape)
    output_lines.append("=" * 60)
    output_lines.append("INJURIES (LATEST SCRAPE)")
    output_lines.append("=" * 60)
    output_lines.append("")

    if upcoming and injuries_by_team:
        any_injuries = False
        for game in upcoming:
            if not game.game_id:
                continue
            meta = game_map.get(game.game_id, {})
            home_name = meta.get("home_team_name") or game.home_team_name or "Home"
            away_name = meta.get("away_team_name") or game.away_team_name or "Away"
            home_team_id = meta.get("home_team_id") or team_id_by_name.get(home_name)
            away_team_id = meta.get("away_team_id") or team_id_by_name.get(away_name)

            home_key = home_team_id
            away_key = away_team_id
            if home_key and "-" in home_key:
                home_key_alt = home_key.split("-")[-1]
            else:
                home_key_alt = None
            if away_key and "-" in away_key:
                away_key_alt = away_key.split("-")[-1]
            else:
                away_key_alt = None

            home_injuries = injuries_by_team.get(home_key, []) if home_key else []
            if not home_injuries and home_key_alt:
                home_injuries = injuries_by_team.get(home_key_alt, [])

            away_injuries = injuries_by_team.get(away_key, []) if away_key else []
            if not away_injuries and away_key_alt:
                away_injuries = injuries_by_team.get(away_key_alt, [])

            if not home_injuries and not away_injuries:
                continue

            any_injuries = True
            output_lines.append(f"{away_name} @ {home_name}")
            if home_injuries:
                output_lines.append(f"{home_name} Injuries:")
                for inj in home_injuries:
                    desc = f" - {inj['description']}" if inj.get("description") else ""
                    output_lines.append(f"  - {inj['player_name']} ({inj['status']}){desc}")
            if away_injuries:
                output_lines.append(f"{away_name} Injuries:")
                for inj in away_injuries:
                    desc = f" - {inj['description']}" if inj.get("description") else ""
                    output_lines.append(f"  - {inj['player_name']} ({inj['status']}){desc}")
            output_lines.append("")

        if not any_injuries:
            output_lines.append("No injuries listed for upcoming teams.")
            output_lines.append("")
    else:
        output_lines.append("No injuries listed for upcoming teams.")
        output_lines.append("")
    
    return {
        "text": "\n".join(output_lines),
        "yesterday_count": len(results),
        "today_count": len(upcoming)
    }


@router.get("/{game_id}")
async def game_intel(game_id: str, session: AsyncSession = Depends(get_session)):
    svc = GameIntelligenceService(session)
    return await svc.get_game_intel(game_id)