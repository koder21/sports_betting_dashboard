from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo
import logging

from ..db import get_session
from ..services.intelligence.game_intel import GameIntelligenceService
from ..services.aai.fresh_data_scraper import FreshDataScraper
from ..models.games_results import GameResult
from ..models.games_upcoming import GameUpcoming
from ..models.games_live import GameLive
from ..models.game import Game
from ..models.injury import Injury
from ..models.player import Player
from ..models.team import Team

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{game_id}")
async def redirect_game_details(game_id: str):
    """Redirect /games/{game_id} to /games/{game_id}/detailed"""
    return RedirectResponse(url=f"/games/{game_id}/detailed", status_code=301)



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
    
    # Get yesterday's results (games that STARTED during yesterday PST)
    # Query GameResult for completed games from yesterday
    yesterday_from_results = await session.execute(
        select(GameResult)
        .where(
            and_(
                GameResult.start_time >= yesterday_start_utc,
                GameResult.start_time < today_start_utc
            )
        )
        .order_by(GameResult.start_time)
    )
    results = list(yesterday_from_results.scalars().all())
    
    # Also check GameLive for games with final status that started yesterday
    # Get ALL GameLive games and check their actual start times from Game/GameUpcoming tables
    all_live_result = await session.execute(select(GameLive))
    all_live_games = all_live_result.scalars().all()
    
    game_ids_in_results = {g.game_id for g in results if g.game_id}
    game_ids_to_lookup = [g.game_id for g in all_live_games if g.game_id and g.game_id not in game_ids_in_results]
    
    # OPTIMIZATION: Bulk fetch GameUpcoming and Game records concurrently (2x speedup)
    upcoming_lookup = {}
    game_lookup = {}
    
    if game_ids_to_lookup:
        import asyncio
        # Concurrent queries: fetch both tables at same time to reduce wait time
        upcoming_result, game_result = await asyncio.gather(
            session.execute(
                select(GameUpcoming).where(GameUpcoming.game_id.in_(game_ids_to_lookup))
            ),
            session.execute(
                select(Game).where(Game.game_id.in_(game_ids_to_lookup))
            ),
            return_exceptions=False
        )
        upcoming_lookup = {r.game_id: r for r in upcoming_result.scalars()}
        game_lookup = {g.game_id: g for g in game_result.scalars()}
    
    game_start_times = {}  # Map to store start times for sorting
    
    for game_live in all_live_games:
        if game_live.game_id in game_ids_in_results:
            continue
        
        # Check if this game is "final" status
        status_detail = game_live.status or ""
        if not ("Final" in status_detail or "FT" in status_detail or status_detail == "Full Time"):
            continue
        
        # Get the actual start time from pre-fetched lookups (no queries in loop)
        start_time = None
        
        # Try GameUpcoming first
        upcoming_record = upcoming_lookup.get(game_live.game_id)
        if upcoming_record and upcoming_record.start_time:
            start_time = upcoming_record.start_time
        
        # Fallback to Game table if no upcoming found
        if not start_time:
            game_record = game_lookup.get(game_live.game_id)
            if game_record and game_record.start_time:
                start_time = game_record.start_time
        # Check if start time is in yesterday's range
        if start_time:
            # Handle timezone-aware datetimes
            start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            if yesterday_start_utc <= start_time_naive < today_start_utc:
                results.append(game_live)
                game_start_times[game_live.game_id] = start_time_naive
    
    # Sort by start_time - use stored times for GameLive, use start_time attribute for GameResult
    def get_sort_key(game):
        if hasattr(game, 'start_time') and game.start_time:
            return game.start_time
        elif game.game_id in game_start_times:
            return game_start_times[game.game_id]
        else:
            return datetime.min
    
    results = sorted(results, key=get_sort_key)
    
    # Get all current live games (GameLive contains all games currently being tracked)
    # Join with Game to get start_time for filtering
    all_live_games_query = await session.execute(
        select(GameLive, Game.start_time)
        .join(Game, GameLive.game_id == Game.game_id)
        .order_by(Game.start_time.asc())
    )
    all_live_games_rows = all_live_games_query.all()
    
    # Convert to today's end time in UTC for filtering if needed
    today_end_pst = datetime.combine(today_pst + timedelta(days=1), datetime.min.time()).replace(tzinfo=pst)
    today_end_utc = today_end_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    
    # Filter for upcoming games (not final, or currently live) that start today or later
    upcoming = [
        game_live for game_live, start_time in all_live_games_rows 
        if start_time and (start_time.replace(tzinfo=None) if start_time.tzinfo else start_time) >= today_start_utc and 
           (not game_live.status or ("Final" not in str(game_live.status) and "FT" not in str(game_live.status)))
    ]
    
    # Build game/team mapping for injuries (no re-scrape, DB only)
    game_id_list = [game.game_id for game in upcoming if game.game_id]
    game_map: Dict[str, Dict[str, str | None]] = {}
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

    injuries_by_team: Dict[str, List[Dict[str, str | None]]] = {}
    if upcoming:
        team_names = list({
            name for game in upcoming
            for name in [game.home_team_name, game.away_team_name]
            if name
        })
    else:
        team_names = []

    if team_ids or team_names:
        # Build filter clauses dynamically
        filter_clauses = []
        if team_ids:
            filter_clauses.append(Team.team_id.in_(team_ids))
        if team_names:
            filter_clauses.append(Team.name.in_(team_names))
            filter_clauses.append(Team.abbreviation.in_(team_names))
        
        team_rows = await session.execute(
            select(Team).where(or_(*filter_clauses))
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


@router.get("/ai-context-fresh")
async def get_ai_context_fresh(session: AsyncSession = Depends(get_session)):
    """
    Get yesterday's results and today's upcoming games for AI analysis.
    FIRST runs fresh scrapes to get the most recent data:
    - Today's upcoming games
    - Latest injuries
    - Weather forecasts
    """
    try:
        # Run fresh scrapes first
        logger.info("Starting fresh data scrape for AI context...")
        fresh_scraper = FreshDataScraper(session)
        try:
            # Scrape today's games
            logger.info("  📅 Scraping today's upcoming games...")
            games_count = await fresh_scraper._scrape_todays_games()
            
            # Scrape injuries
            logger.info("  🏥 Scraping latest injuries...")
            injuries_count = await fresh_scraper._scrape_injuries()
            
            # Update weather forecasts
            logger.info("  🌦️ Updating weather forecasts...")
            weather_count = await fresh_scraper._update_weather()
            
            logger.info(f"Fresh scrape complete: {games_count} games, {injuries_count} injuries, {weather_count} weather forecasts")
        finally:
            await fresh_scraper.close()
    except Exception as e:
        logger.error(f"Fresh scrape failed: {str(e)}", exc_info=True)
        # Continue with existing data if scrape fails
        pass
    
    # Now get the AI context with fresh data
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
    
    # Get yesterday's results (games that STARTED during yesterday PST)
    # Query GameResult for completed games from yesterday
    yesterday_from_results = await session.execute(
        select(GameResult)
        .where(
            and_(
                GameResult.start_time >= yesterday_start_utc,
                GameResult.start_time < today_start_utc
            )
        )
        .order_by(GameResult.start_time)
    )
    results = list(yesterday_from_results.scalars().all())
    
    # Also check GameLive for games with final status that started yesterday
    # Get ALL GameLive games and check their actual start times from Game/GameUpcoming tables
    all_live_result = await session.execute(select(GameLive))
    all_live_games = all_live_result.scalars().all()
    
    game_ids_in_results = {g.game_id for g in results if g.game_id}
    game_ids_to_lookup = [g.game_id for g in all_live_games if g.game_id and g.game_id not in game_ids_in_results]
    
    # OPTIMIZATION: Bulk fetch GameUpcoming and Game records concurrently (2x speedup)
    upcoming_lookup = {}
    game_lookup = {}
    
    if game_ids_to_lookup:
        import asyncio
        # Concurrent queries: fetch both tables at same time to reduce wait time
        upcoming_result, game_result = await asyncio.gather(
            session.execute(
                select(GameUpcoming).where(GameUpcoming.game_id.in_(game_ids_to_lookup))
            ),
            session.execute(
                select(Game).where(Game.game_id.in_(game_ids_to_lookup))
            ),
            return_exceptions=False
        )
        upcoming_lookup = {r.game_id: r for r in upcoming_result.scalars()}
        game_lookup = {g.game_id: g for g in game_result.scalars()}
    
    game_start_times = {}  # Map to store start times for sorting
    
    for game_live in all_live_games:
        if game_live.game_id in game_ids_in_results:
            continue
        
        # Check if this game is "final" status
        status_detail = game_live.status or ""
        if not ("Final" in status_detail or "FT" in status_detail or status_detail == "Full Time"):
            continue
        
        # Get the actual start time from pre-fetched lookups (no queries in loop)
        start_time = None
        
        # Try GameUpcoming first
        upcoming_record = upcoming_lookup.get(game_live.game_id)
        if upcoming_record and upcoming_record.start_time:
            start_time = upcoming_record.start_time
        
        # Fallback to Game table if no upcoming found
        if not start_time:
            game_record = game_lookup.get(game_live.game_id)
            if game_record and game_record.start_time:
                start_time = game_record.start_time
        # Check if start time is in yesterday's range
        if start_time:
            # Handle timezone-aware datetimes
            start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            if yesterday_start_utc <= start_time_naive < today_start_utc:
                results.append(game_live)
                game_start_times[game_live.game_id] = start_time_naive
    
    # Sort by start_time - use stored times for GameLive, use start_time attribute for GameResult
    def get_sort_key(game):
        if hasattr(game, 'start_time') and game.start_time:
            return game.start_time
        elif game.game_id in game_start_times:
            return game_start_times[game.game_id]
        else:
            return datetime.min
    
    results = sorted(results, key=get_sort_key)
    
    # Get all current live games (GameLive contains all games currently being tracked)
    # Join with Game to get start_time for filtering
    all_live_games_query = await session.execute(
        select(GameLive, Game.start_time)
        .join(Game, GameLive.game_id == Game.game_id)
        .order_by(Game.start_time.asc())
    )
    all_live_games_rows = all_live_games_query.all()
    
    # Convert to today's end time in UTC for filtering if needed
    today_end_pst = datetime.combine(today_pst + timedelta(days=1), datetime.min.time()).replace(tzinfo=pst)
    today_end_utc = today_end_pst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    
    # Filter for upcoming games (not final, or currently live) that start today or later
    upcoming = [
        game_live for game_live, start_time in all_live_games_rows 
        if start_time and (start_time.replace(tzinfo=None) if start_time.tzinfo else start_time) >= today_start_utc and 
           (not game_live.status or ("Final" not in str(game_live.status) and "FT" not in str(game_live.status)))
    ]
    
    # Build game/team mapping for injuries (no re-scrape, DB only)
    game_id_list = [game.game_id for game in upcoming if game.game_id]
    game_map: Dict[str, Dict[str, str | None]] = {}
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

    injuries_by_team: Dict[str, List[Dict[str, str | None]]] = {}
    if upcoming:
        team_names = list({
            name for game in upcoming
            for name in [game.home_team_name, game.away_team_name]
            if name
        })
    else:
        team_names = []

    if team_ids or team_names:
        # Build filter clauses dynamically
        filter_clauses = []
        if team_ids:
            filter_clauses.append(Team.team_id.in_(team_ids))
        if team_names:
            filter_clauses.append(Team.name.in_(team_names))
            filter_clauses.append(Team.abbreviation.in_(team_names))
        
        team_rows = await session.execute(
            select(Team).where(or_(*filter_clauses))
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


@router.get("/{game_id}/detailed")
async def get_game_details(game_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get comprehensive game details including:
    - Game info and scores
    - Team stats and player stats
    - Bets on this game with live performance tracking
    - Box score and play-by-play data
    """
    from sqlalchemy.orm import selectinload
    from ..models.player_stats import PlayerStats
    from ..models.bet import Bet
    
    # Fetch game from all three states (upcoming, live, result)
    # OPTIMIZATION: Use eager loading for teams to prevent N+1 queries
    game_result = await session.execute(
        select(Game)
        .where(Game.game_id == game_id)
        .options(
            selectinload(Game.home_team),
            selectinload(Game.away_team)
        )
    )
    game = game_result.scalar()
    
    if not game:
        return {"error": f"Game {game_id} not found"}
    
    # Get game status from state tables
    game_upcoming_result = await session.execute(
        select(GameUpcoming).where(GameUpcoming.game_id == game_id)
    )
    game_upcoming = game_upcoming_result.scalar()
    
    game_live_result = await session.execute(
        select(GameLive).where(GameLive.game_id == game_id)
    )
    game_live = game_live_result.scalar()
    
    game_result_result = await session.execute(
        select(GameResult).where(GameResult.game_id == game_id)
    )
    game_result_obj = game_result_result.scalar()
    
    # Determine current status and use appropriate data
    current_status = "upcoming"
    status_obj = game_upcoming
    if game_live:
        current_status = "live"
        status_obj = game_live
    if game_result_obj:
        current_status = "final"
        status_obj = game_result_obj
    
    # Get teams with relationships
    home_team = game.home_team
    away_team = game.away_team
    
    # Get all player stats for this game
    player_stats_result = await session.execute(
        select(PlayerStats)
        .where(PlayerStats.game_id == game_id)
        .options(selectinload(PlayerStats.player))
    )
    all_player_stats = player_stats_result.scalars().all()
    
    # Organize player stats by team - handle both integer and prefixed team_ids
    # Extract the numeric part from team_ids for matching (e.g., "NBA-11" -> "11")
    def get_numeric_team_id(team_id):
        """Extract numeric part from team_id (e.g., 'NBA-11' -> '11' or 11 -> '11')"""
        if not team_id:
            return None
        team_id_str = str(team_id)
        if '-' in team_id_str:
            return team_id_str.split('-')[1]
        return team_id_str
    
    home_numeric_id = get_numeric_team_id(game.home_team_id)
    away_numeric_id = get_numeric_team_id(game.away_team_id)
    
    # Filter players by matching either the full team_id or the numeric part
    home_player_stats = [
        ps for ps in all_player_stats 
        if str(ps.team_id) == home_numeric_id or str(ps.team_id) == game.home_team_id
    ]
    away_player_stats = [
        ps for ps in all_player_stats 
        if str(ps.team_id) == away_numeric_id or str(ps.team_id) == game.away_team_id
    ]
    
    # Calculate team aggregates
    def calculate_team_stats(player_stats_list):
        if not player_stats_list:
            return {}
        totals = {
            "points": sum(ps.points or 0 for ps in player_stats_list),
            "rebounds": sum(ps.rebounds or 0 for ps in player_stats_list),
            "assists": sum(ps.assists or 0 for ps in player_stats_list),
            "steals": sum(ps.steals or 0 for ps in player_stats_list),
            "blocks": sum(ps.blocks or 0 for ps in player_stats_list),
            "turnovers": sum(ps.turnovers or 0 for ps in player_stats_list),
            "player_count": len(player_stats_list)
        }
        return totals
    
    home_team_stats = calculate_team_stats(home_player_stats)
    away_team_stats = calculate_team_stats(away_player_stats)
    
    # Get bets on this game
    bets_result = await session.execute(
        select(Bet)
        .where(Bet.game_id == game_id)
        .options(selectinload(Bet.player))
        .order_by(Bet.placed_at.desc())
    )
    bets = bets_result.scalars().all()
    
    # Enrich bets with current player performance
    enriched_bets = []
    for bet in bets:
        bet_data = {
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
            "current_performance": None
        }
        
        # If this is a player prop, find current stats
        if bet.player_id and bet.player:
            player_stat = next((ps for ps in all_player_stats if ps.player_id == bet.player_id), None)
            if player_stat:
                # Get the stat value based on stat_type
                stat_value = None
                stat_display = None
                if bet.stat_type:
                    stat_type_lower = bet.stat_type.lower()
                    if "points" in stat_type_lower or "pts" in stat_type_lower:
                        stat_value = player_stat.points
                        stat_display = f"{stat_value} PTS"
                    elif "rebounds" in stat_type_lower or "reb" in stat_type_lower:
                        stat_value = player_stat.rebounds
                        stat_display = f"{stat_value} REB"
                    elif "assists" in stat_type_lower or "ast" in stat_type_lower:
                        stat_value = player_stat.assists
                        stat_display = f"{stat_value} AST"
                    elif "steals" in stat_type_lower or "stl" in stat_type_lower:
                        stat_value = player_stat.steals
                        stat_display = f"{stat_value} STL"
                    elif "blocks" in stat_type_lower or "blk" in stat_type_lower:
                        stat_value = player_stat.blocks
                        stat_display = f"{stat_value} BLK"
                    elif "3-pointers" in stat_type_lower or "3pt" in stat_type_lower:
                        stat_value = player_stat.three_pt
                        stat_display = f"{stat_value} 3PT"
                    elif "passing yards" in stat_type_lower:
                        stat_value = player_stat.passing_yards
                        stat_display = f"{stat_value} YDS"
                    elif "touchdowns" in stat_type_lower:
                        stat_value = player_stat.passing_tds or player_stat.receiving_tds
                        stat_display = f"{stat_value} TD"
                    elif "rushing yards" in stat_type_lower:
                        stat_value = player_stat.rushing_yards
                        stat_display = f"{stat_value} YDS"
                
                bet_data["current_performance"] = {
                    "player_id": bet.player_id,
                    "player_name": bet.player.name or bet.player.full_name,
                    "stat_value": stat_value,
                    "stat_display": stat_display,
                    "team_id": player_stat.team_id,
                    "headshot": bet.player.headshot,
                    "jersey": bet.player.jersey,
                }
        
        enriched_bets.append(bet_data)
    
    return {
        "game": {
            "game_id": game.game_id,
            "sport": game.sport,
            "league": game.league,
            "status": current_status,
            "start_time": game.start_time.isoformat() if game.start_time else None,
            "venue": game.venue,
            "home": {
                "team_id": game.home_team_id,
                "team_name": game.home_team_name,
                "logo": home_team.logo if home_team else None,
                "score": game.home_score,
                "stats": home_team_stats
            },
            "away": {
                "team_id": game.away_team_id,
                "team_name": game.away_team_name,
                "logo": away_team.logo if away_team else None,
                "score": game.away_score,
                "stats": away_team_stats
            },
            "period": game.period,
            "clock": game.clock,
            "boxscore_json": game.boxscore_json,
            "play_by_play_json": game.play_by_play_json,
        },
        "home_players": [
            {
                "player_id": ps.player_id,
                "player_name": ps.player.name or ps.player.full_name if ps.player else "Unknown",
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
                "player_name": ps.player.name or ps.player.full_name if ps.player else "Unknown",
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
async def get_scraper_metrics():
    """Get performance metrics for all scraping operations"""
    from ..services.metrics import metrics_collector
    
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
        ]
    }


@router.post("/{game_id}/refresh-stats")
async def refresh_game_stats(game_id: str, session: AsyncSession = Depends(get_session)):
    """
    Manually refresh player stats for a specific game.
    Triggers immediate scrape of player statistics from ESPN.
    """
    from ..services.scraper_stats import PlayerStatsScraper
    from ..services.espn_client import ESPNClient
    
    client = ESPNClient()
    try:
        # Get the game to find its league
        game_result = await session.execute(
            select(Game).where(Game.game_id == game_id)
        )
        game = game_result.scalar()
        
        if not game:
            return {"error": f"Game {game_id} not found", "success": False}
        
        # Map sport to ESPN league identifier
        sport_league_map = {
            "NBA": ("basketball", "nba"),
            "NCAAB": ("basketball", "mens-college-basketball"),
            "NFL": ("football", "nfl"),
            "NCAAF": ("football", "college-football"),
            "NHL": ("hockey", "nhl"),
            "UFC": ("mma", "ufc"),
            "EPL": ("soccer", "eng.1"),
            "SOCCER": ("soccer", "eng.1"),
        }
        
        sport_upper = (game.sport or "").upper()
        if sport_upper not in sport_league_map:
            return {"error": f"Unknown sport: {game.sport}", "success": False}
        
        sport_type, league = sport_league_map[sport_upper]
        
        # Scrape stats for this specific game
        stats_scraper = PlayerStatsScraper(client, session)
        
        # Scrape the boxscore with correct parameters
        await stats_scraper._scrape_game_boxscore(game_id, sport_type, league, sport_upper)
        
        return {
            "success": True,
            "message": f"Player stats refreshed for game {game_id}",
            "game_id": game_id,
            "sport": game.sport
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "details": traceback.format_exc()
        }
    finally:
        await client.close()