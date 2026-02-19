"""
Database backup service with 6-hour intervals.
Backs up to timestamped files in backups/ directory.
"""
import os
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("db_backup")

# Configuration
BACKUP_DIR = Path.home() / "sports_betting_dashboard" / "backups"
BACKUP_STATE_FILE = BACKUP_DIR / ".backup_state.json"
BACKUP_FILE_PREFIX = "sports_intel_backup_"
BACKUP_INTERVAL_HOURS = 6
KEEP_BACKUP_COUNT = 8  # Keep last 48 hours worth (8 * 6hr = 48hr)

# Database configuration (read from environment)
PG_DB_NAME = os.getenv("PG_DB_NAME", "sports_intel")
PG_USER = os.getenv("PG_USER", "sbd")
PG_PASSWORD = os.getenv("PG_PASSWORD", "sbddb")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")


def ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_last_backup_time() -> datetime | None:
    """Get the timestamp of the last backup from state file."""
    try:
        with open(BACKUP_STATE_FILE, "r") as f:
            state = json.load(f)
            return datetime.fromisoformat(state.get("last_backup_utc"))
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError):
        return None


def set_last_backup_time(dt: datetime):
    """Save the timestamp of the last backup to state file."""
    state = {"last_backup_utc": dt.isoformat()}
    with open(BACKUP_STATE_FILE, "w") as f:
        json.dump(state, f)


def should_backup_now() -> bool:
    """Check if it's time to backup (6 hours since last backup)."""
    last_backup = get_last_backup_time()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if last_backup is None:
        return True  # First backup ever

    time_since_last = now - last_backup
    return time_since_last >= timedelta(hours=BACKUP_INTERVAL_HOURS)


def create_backup() -> bool:
    """Create a timestamped backup of the database."""
    ensure_backup_dir()

    try:
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{BACKUP_FILE_PREFIX}{timestamp}.sql"

        # Use pg_dump to create PostgreSQL backup
        cmd = [
            "pg_dump",
            f"-U{PG_USER}",
            f"-h{PG_HOST}",
            f"-p{PG_PORT}",
            "-Fc",  # Custom format (compressed)
            "-f", str(backup_path),
            PG_DB_NAME,
        ]
        
        # Set PGPASSWORD environment variable
        env = {**os.environ, "PGPASSWORD": PG_PASSWORD}
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return False

        logger.info(f"✓ Backup created: {backup_path.name}")

        # Update last backup time
        set_last_backup_time(datetime.now(timezone.utc).replace(tzinfo=None))

        # Clean up old backups
        cleanup_old_backups()

        return True

    except subprocess.TimeoutExpired:
        logger.error("Backup timeout (5 minutes)")
        return False
    except Exception as e:
        logger.exception(f"✗ Backup failed: {e}")
        return False


def cleanup_old_backups(keep_count: int = KEEP_BACKUP_COUNT):
    """Remove old backups, keeping only the most recent ones."""
    try:
        # FIX: Use .sql extension, not .db
        backup_files = sorted(
            BACKUP_DIR.glob(f"{BACKUP_FILE_PREFIX}*.sql"),
            key=lambda p: p.stat().st_mtime
        )

        if len(backup_files) > keep_count:
            for old_backup in backup_files[:-keep_count]:
                old_backup.unlink()
                logger.info(f"Cleaned up old backup: {old_backup.name}")

    except Exception as e:
        logger.warning(f"Backup cleanup error: {e}")


async def backup_job() -> bool:
    """Async job to check and run backups."""
    if should_backup_now():
        return create_backup()
    return False


def init_backup_logging():
    """Initialize logging for backup service."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] DB_BACKUP: %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def restore_backup(backup_file: Path) -> bool:
    """
    Restore database from backup file.
    
    WARNING: This will drop and recreate the database!
    """
    try:
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False

        # Use pg_restore for custom format backups
        cmd = [
            "pg_restore",
            f"-U{PG_USER}",
            f"-h{PG_HOST}",
            f"-p{PG_PORT}",
            "--clean",  # Drop objects before recreating
            "--if-exists",  # Don't error if objects don't exist
            "-d", PG_DB_NAME,
            str(backup_file),
        ]
        
        env = {**os.environ, "PGPASSWORD": PG_PASSWORD}
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"pg_restore failed: {result.stderr}")
            return False

        logger.info(f"✓ Database restored from: {backup_file.name}")
        return True

    except Exception as e:
        logger.exception(f"✗ Restore failed: {e}")
        return False


if __name__ == "__main__":
    # Test the backup
    init_backup_logging()
    logger.info("Starting database backup test...")
    
    success = create_backup()
    
    if success:
        logger.info("Backup test completed successfully")
        last_backup = get_last_backup_time()
        if last_backup:
            next_backup = last_backup + timedelta(hours=BACKUP_INTERVAL_HOURS)
            logger.info(f"Next scheduled backup: {next_backup}")
    else:
        logger.error("Backup test failed")