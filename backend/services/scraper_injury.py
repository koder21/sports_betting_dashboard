from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
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
    player_rows = []
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
        if len(description) > 512:
            description = description[:512]
        status = injury.get("status") or injury.get("type") or ""
        last_updated_raw = injury.get("lastUpdated") or injury.get("dateUpdated")
        if isinstance(last_updated_raw, str) and last_updated_raw:
            try:
                last_updated = datetime.fromisoformat(last_updated_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                last_updated = None
        else:
            last_updated = last_updated_raw
        if not player_id or not team_id:
            continue
        player_rows.append(dict(
            player_id=player_id,
            name=injury.get("playerName") or injury.get("displayName") or None,
            full_name=injury.get("playerName") or injury.get("displayName") or None,
            team_id=team_id,
            sport=sport_prefix,
            league=sport_prefix,
        ))
        team_rows.append(dict(team_id=team_id, name=injury.get("team_name") or None))
        injury_rows.append(dict(
            player_id=player_id,
            team_id=team_id,
            description=description,
            status=status,
            last_updated=last_updated,
        ))
    # Upsert teams first (deduplicate by team_id to avoid CardinalityViolationError)
    if team_rows:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        seen_team_ids = set()
        unique_team_rows = []
        for row in team_rows:
            if row["team_id"] not in seen_team_ids:
                seen_team_ids.add(row["team_id"])
                unique_team_rows.append(row)
        TEAM_BATCH_SIZE = 100
        for i in range(0, len(unique_team_rows), TEAM_BATCH_SIZE):
            batch = unique_team_rows[i:i+TEAM_BATCH_SIZE]
            try:
                team_stmt = pg_insert(Team).values(batch)
                team_stmt = team_stmt.on_conflict_do_nothing(index_elements=["team_id"])
                await session.execute(team_stmt)
            except Exception as e:
                # If batch fails, try inserting teams one by one
                failed_team_ids = []
                for row in batch:
                    try:
                        team_stmt = pg_insert(Team).values([row])
                        team_stmt = team_stmt.on_conflict_do_nothing(index_elements=["team_id"])
                        await session.execute(team_stmt)
                    except Exception as inner_e:
                        failed_team_ids.append(row["team_id"])
                if failed_team_ids:
                    print(f"[InjuryUpsert] Failed to insert teams: {failed_team_ids} (error: {e})")
        await session.flush()
    # Upsert players (stub rows to satisfy FK; deduplicate by player_id)
    if player_rows:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        seen_player_ids = set()
        unique_player_rows = []
        for row in player_rows:
            if row["player_id"] not in seen_player_ids:
                seen_player_ids.add(row["player_id"])
                unique_player_rows.append(row)
        player_stmt = pg_insert(Player).values(unique_player_rows)
        player_stmt = player_stmt.on_conflict_do_nothing(index_elements=["player_id"])
        await session.execute(player_stmt)
    await session.flush()
    # Upsert injuries using bulk executemany - one round trip per 250 rows
    # instead of 1244 individual INSERT round trips that cause statement timeouts
    if injury_rows:
        from sqlalchemy import text
        BATCH_SIZE = 250
        for i in range(0, len(injury_rows), BATCH_SIZE):
            batch = injury_rows[i:i + BATCH_SIZE]
            await session.execute(
                text("""
                    INSERT INTO injuries (player_id, team_id, description, status, last_updated)
                    VALUES (:player_id, :team_id, :description, :status, :last_updated)
                    ON CONFLICT (player_id, team_id, description)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        last_updated = EXCLUDED.last_updated
                """),
                batch,
            )
        await session.flush()