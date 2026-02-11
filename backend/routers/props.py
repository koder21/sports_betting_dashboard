from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..services.intelligence.prop_intel import PropIntelligenceService
from ..models.player import Player
from ..models.player_stats import PlayerStats
from ..models.team import Team

router = APIRouter()


@router.get("/players")
async def get_all_players(session: AsyncSession = Depends(get_session)):
    """Get all players with basic info - team matched by both team_id and sport.
    
    OPTIMIZED: Uses eager loading to avoid N+1 query problem.
    """
    # Check if Player model has team relationship
    try:
        # Try with eager loading first (if relationship exists)
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Player).options(
                selectinload(Player.team)
            ).order_by(Player.full_name)
        )
        players = result.scalars().unique().all()
        
        player_list = []
        for p in players:
            team_name = None
            if hasattr(p, 'team') and p.team:
                team_name = p.team.name
            
            player_list.append({
                "player_id": p.player_id,
                "full_name": p.full_name,
                "name": p.name,
                "position": p.position,
                "team_id": p.team_id,
                "team_name": team_name,
                "sport": p.sport,
                "league": p.league,
                "headshot": p.headshot,
                "jersey": p.jersey,
                "active": p.active,
            })
        
        return player_list
    
    except Exception:
        # Fallback: If relationship doesn't exist, use bulk lookup pattern
        result = await session.execute(
            select(Player).order_by(Player.full_name)
        )
        players = result.scalars().all()
        
        # Bulk fetch teams to avoid N+1
        team_filters = [
            and_(Team.team_id == p.team_id, Team.sport_name == p.sport)
            for p in players
            if p.team_id and p.sport
        ]
        
        teams = {}
        if team_filters:
            team_result = await session.execute(
                select(Team).where(or_(*team_filters))
            )
            teams = {
                (t.team_id, t.sport_name): t.name 
                for t in team_result.scalars()
            }
        
        player_list = []
        for p in players:
            team_name = None
            if p.team_id and p.sport:
                team_name = teams.get((p.team_id, p.sport))
            
            player_list.append({
                "player_id": p.player_id,
                "full_name": p.full_name,
                "name": p.name,
                "position": p.position,
                "team_id": p.team_id,
                "team_name": team_name,
                "sport": p.sport,
                "league": p.league,
                "headshot": p.headshot,
                "jersey": p.jersey,
                "active": p.active,
            })
        
        return player_list


@router.get("/players/{player_id}/stats")
async def get_player_stats(player_id: str, session: AsyncSession = Depends(get_session)):
    """Get all stats for a specific player"""
    result = await session.execute(
        select(PlayerStats)
        .where(PlayerStats.player_id == player_id)
        .order_by(PlayerStats.id.desc())
    )
    stats = result.scalars().all()
    return [
        {
            "id": s.id,
            "game_id": s.game_id,
            "player_id": s.player_id,
            "team_id": s.team_id,
            "sport": s.sport,
            "minutes": s.minutes,
            "points": s.points,
            "rebounds": s.rebounds,
            "assists": s.assists,
            "steals": s.steals,
            "blocks": s.blocks,
            "turnovers": s.turnovers,
            "fg": s.fg,
            "three_pt": s.three_pt,
            "ft": s.ft,
            "passing_yards": s.passing_yards,
            "passing_tds": s.passing_tds,
            "interceptions": s.interceptions,
            "rushing_yards": s.rushing_yards,
            "rushing_tds": s.rushing_tds,
            "receiving_yards": s.receiving_yards,
            "receiving_tds": s.receiving_tds,
            "tackles": s.tackles,
            "sacks": s.sacks,
        }
        for s in stats
    ]


@router.get("/{player_id}/{market}")
async def prop_intel(player_id: int, market: str, session: AsyncSession = Depends(get_session)):
    svc = PropIntelligenceService(session)
    return await svc.suggest_prop(player_id, market)