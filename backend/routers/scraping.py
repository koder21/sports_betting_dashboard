from fastapi import APIRouter, Depends
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..db import get_session, AsyncSessionLocal
from ..services.espn_client import ESPNClient
from ..services.scraping import (
    NFLScraper,
    NBAScraper,
    NCAAFScraper,
    NCAABScraper,
    NHLScraper,
    SoccerScraper,
    UFCScraper,
)

router = APIRouter(prefix="/scrape", tags=["scrape"])

# In-memory job tracking for long-running tasks
FILL_NAME_JOBS = {}


@router.post("/sport/{sport_name}")
async def scrape_sport(sport_name: str, session: AsyncSession = Depends(get_session)):
    client = ESPNClient()
    try:
        if sport_name == "nfl":
            scraper = NFLScraper(session, client)
        elif sport_name == "nba":
            scraper = NBAScraper(session, client)
        elif sport_name == "ncaaf":
            scraper = NCAAFScraper(session, client)
        elif sport_name == "ncaab":
            scraper = NCAABScraper(session, client)
        elif sport_name == "nhl":
            scraper = NHLScraper(session, client)
        elif sport_name == "soccer":
            scraper = SoccerScraper(session, client)
        elif sport_name == "ufc":
            scraper = UFCScraper(session, client)
        else:
            return {"error": "unknown sport"}
        await scraper.scrape()
        return {"status": "ok"}
    finally:
        await client.close()


@router.post("/fix-orphaned-players")
async def fix_orphaned_players(session: AsyncSession = Depends(get_session)):
    """
    Create player records for all orphaned player_ids in player_stats.
    This fixes the issue where player_stats exist but the player doesn't.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get all unique player_ids from player_stats that don't have a player record
        result = await session.execute(
            text("""
                SELECT DISTINCT ps.player_id, ps.sport
                FROM player_stats ps
                LEFT JOIN players p ON ps.player_id = p.player_id
                WHERE p.player_id IS NULL
            """)
        )
        
        orphaned = result.fetchall()
        created_count = 0
        failed_count = 0
        errors = []
        
        for player_id, sport in orphaned:
            try:
                # Insert minimal player record with player_id and sport
                await session.execute(
                    text("""
                        INSERT OR IGNORE INTO players (player_id, name, sport)
                        VALUES (:player_id, :name, :sport)
                    """),
                    {"player_id": player_id, "name": f"Player {player_id}", "sport": sport}
                )
                created_count += 1
                await session.commit()  # Commit per record to isolate failures
            except Exception as e:
                failed_count += 1
                await session.rollback()
                error_msg = f"Failed to create player {player_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        return {
            "status": "ok" if failed_count == 0 else "partial",
            "message": f"Created {created_count} players, failed {failed_count}",
            "orphaned_fixed": created_count,
            "orphaned_failed": failed_count,
            "errors": errors[:10]  # Return first 10 errors for debugging
        }
    except Exception as e:
        logger.error("[Scraping] fix-orphaned-players failed: %s", e, exc_info=True)
        await session.rollback()
        return {
            "status": "error",
            "message": f"Batch operation failed: {str(e)}",
            "orphaned_fixed": 0,
            "orphaned_failed": 0
        }


@router.post("/fill-player-names")
async def fill_player_names(limit: int = 100, session: AsyncSession = Depends(get_session)):
    """
    Fill placeholder player names ("Player ####") using ESPN athlete data.
    """
    client = ESPNClient()
    try:
        total_result = await session.execute(
            text("""
                SELECT COUNT(*)
                FROM players
                WHERE name IS NULL OR name LIKE 'Player %'
            """)
        )
        total_remaining = total_result.scalar() or 0

        result = await session.execute(
            text("""
                SELECT player_id, sport, name
                FROM players
                WHERE name IS NULL OR name LIKE 'Player %'
                LIMIT :limit
            """),
            {"limit": limit}
        )

        rows = result.fetchall()
        updated = 0
        skipped = 0

        sport_map = {
            "NBA": ("basketball", "nba"),
            "NCAAB": ("basketball", "mens-college-basketball"),
            "NFL": ("football", "nfl"),
            "NCAAF": ("football", "college-football"),
            "NHL": ("hockey", "nhl"),
            "MLB": ("baseball", "mlb"),
            "WNBA": ("basketball", "wnba"),
            "UFC": ("mma", "ufc"),
            "SOCCER": ("soccer", "eng.1"),
            "EPL": ("soccer", "eng.1"),
        }

        for player_id, sport, _name in rows:
            sport_key = (sport or "").upper()
            if sport_key not in sport_map:
                skipped += 1
                continue

            sport_type, league = sport_map[sport_key]
            athlete_url = (
                f"https://site.web.api.espn.com/apis/common/v3/sports/"
                f"{sport_type}/{league}/athletes/{player_id}"
            )
            athlete_data = await client.get_json(athlete_url)
            if not athlete_data:
                skipped += 1
                continue

            athlete = athlete_data.get("athlete", {}) or athlete_data
            new_name = (
                athlete.get("displayName")
                or athlete.get("fullName")
                or athlete.get("shortName")
            )
            if not new_name:
                skipped += 1
                continue

            await session.execute(
                text("""
                    UPDATE players
                    SET name = :name
                    WHERE player_id = :player_id
                """),
                {"name": new_name, "player_id": player_id}
            )
            updated += 1

            if updated % 200 == 0:
                await session.commit()

        await session.commit()

        return {
            "status": "success",
            "updated": updated,
            "skipped": skipped,
            "total_remaining": total_remaining,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        await client.close()


async def _run_fill_player_names_job(job_id: str, limit: int = 200) -> None:
    client = ESPNClient()
    try:
        async with AsyncSessionLocal() as session:
            total_result = await session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM players
                    WHERE name IS NULL OR name LIKE 'Player %'
                """)
            )
            total_remaining = total_result.scalar() or 0

            FILL_NAME_JOBS[job_id].update({
                "status": "running",
                "starting_remaining": total_remaining,
                "remaining": total_remaining,
            })

            sport_map = {
                "NBA": ("basketball", "nba"),
                "NCAAB": ("basketball", "mens-college-basketball"),
                "NFL": ("football", "nfl"),
                "NCAAF": ("football", "college-football"),
                "NHL": ("hockey", "nhl"),
                "MLB": ("baseball", "mlb"),
                "WNBA": ("basketball", "wnba"),
                "UFC": ("mma", "ufc"),
                "SOCCER": ("soccer", "eng.1"),
                "EPL": ("soccer", "eng.1"),
            }

            updated = 0
            skipped = 0

            while True:
                result = await session.execute(
                    text("""
                        SELECT player_id, sport, name
                        FROM players
                        WHERE name IS NULL OR name LIKE 'Player %'
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                rows = result.fetchall()

                if not rows:
                    break

                for player_id, sport, _name in rows:
                    sport_key = (sport or "").upper()
                    if sport_key not in sport_map:
                        skipped += 1
                        continue

                    sport_type, league = sport_map[sport_key]
                    athlete_url = (
                        f"https://site.web.api.espn.com/apis/common/v3/sports/"
                        f"{sport_type}/{league}/athletes/{player_id}"
                    )
                    athlete_data = await client.get_json(athlete_url)
                    if not athlete_data:
                        skipped += 1
                        continue

                    athlete = athlete_data.get("athlete", {}) or athlete_data
                    new_name = (
                        athlete.get("displayName")
                        or athlete.get("fullName")
                        or athlete.get("shortName")
                    )
                    if not new_name:
                        skipped += 1
                        continue

                    await session.execute(
                        text("""
                            UPDATE players
                            SET name = :name
                            WHERE player_id = :player_id
                        """),
                        {"name": new_name, "player_id": player_id}
                    )
                    updated += 1

                await session.commit()

                remaining_result = await session.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM players
                        WHERE name IS NULL OR name LIKE 'Player %'
                    """))
                remaining = remaining_result.scalar() or 0

                FILL_NAME_JOBS[job_id].update({
                    "updated": updated,
                    "skipped": skipped,
                    "remaining": remaining,
                })

            FILL_NAME_JOBS[job_id].update({
                "status": "completed",
                "updated": updated,
                "skipped": skipped,
                "remaining": 0,
            })
    except Exception as e:
        FILL_NAME_JOBS[job_id].update({
            "status": "error",
            "error": str(e),
        })
    finally:
        await client.close()


@router.post("/fill-player-names")
async def fill_player_names(limit: int = 200):
    """
    Start a background job to fill placeholder player names using ESPN athlete data.
    """
    job_id = str(uuid.uuid4())
    FILL_NAME_JOBS[job_id] = {
        "status": "queued",
        "updated": 0,
        "skipped": 0,
        "remaining": None,
        "starting_remaining": None,
    }
    asyncio.create_task(_run_fill_player_names_job(job_id, limit=limit))
    return {"status": "started", "job_id": job_id}


@router.get("/fill-player-names/{job_id}")
async def fill_player_names_status(job_id: str):
    job = FILL_NAME_JOBS.get(job_id)
    if not job:
        return {"status": "error", "message": "job not found"}
    return {"status": "ok", "job": job}
