from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from backend.models.injury import Injury
from backend.models.player import Player
from backend.models.team import Team

async def upsert_injuries(session: AsyncSession, injuries: List[Dict[str, Any]]):
    """
    Upsert all injury records from a list of injury dicts (from ESPN API) into the Injury table.
    Each dict should contain at least: playerId, teamId, description, status, lastUpdated
    """
    # First, batch upsert all teams referenced in injuries
    team_rows = []
    injury_rows = []
    for injury in injuries:
        player_id = str(injury.get("playerId")) or None
        team_id_raw = str(injury.get("teamId")) or None
        sport = injury.get("sport") or injury.get("league") or injury.get("sport_name") or "GEN"
        sport = sport.upper()
        if sport.startswith("NFL"):
            sport_prefix = "NFL"
        elif sport.startswith("NBA"):
            sport_prefix = "NBA"
        elif sport.startswith("NHL"):
            sport_prefix = "NHL"
        elif sport.startswith("MLB"):
            sport_prefix = "MLB"
        elif sport.startswith("NCAAF"):
            sport_prefix = "NCAAF"
        elif sport.startswith("NCAAB"):
            sport_prefix = "NCAAB"
        else:
            sport_prefix = sport
        team_id = f"{sport_prefix}_{team_id_raw}" if team_id_raw else None
        description = injury.get("description") or injury.get("detail") or ""
        status = injury.get("status") or injury.get("type") or ""
        last_updated = injury.get("lastUpdated") or injury.get("dateUpdated")
        if not player_id or not team_id:
            continue
        team_rows.append(dict(team_id=team_id, name=None))
        injury_rows.append(dict(
            player_id=player_id,
            team_id=team_id,
            description=description,
            status=status,
            last_updated=last_updated,
        ))
    # Upsert teams first
    if team_rows:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        team_stmt = pg_insert(Team).values(team_rows)
        team_stmt = team_stmt.on_conflict_do_nothing(index_elements=["team_id"])
        await session.execute(team_stmt)
    await session.flush()
    # Upsert injuries
    for injury in injury_rows:
        stmt = insert(Injury).values(**injury).on_conflict_do_update(
            index_elements=["player_id", "team_id", "description"],
            set_={
                "status": injury["status"],
                "last_updated": injury["last_updated"],
            }
        )
        await session.execute(stmt)
    await session.commit()
