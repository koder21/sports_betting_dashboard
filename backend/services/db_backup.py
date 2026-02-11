"""
Database backup service with 6-hour interval (absolute time, not server uptime).
Backs up to timestamped files in backups/ directory.
Tracks last backup time in a state file to ensure exact 6-hour intervals.
"""

import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import logging

logger = logging.getLogger("db_backup")

BACKUP_DIR = Path.home() / "sports_betting_dashboard" / "backups"
BACKUP_STATE_FILE = BACKUP_DIR / ".backup_state.json"
DB_PATH = Path.home() / "sports_betting_dashboard" / "sports_intel.db"
BACKUP_INTERVAL_HOURS = 6


def ensure_backup_dir():
    """Create backup directory if it doesn't exist"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_last_backup_time():
    """Get the timestamp of the last backup from state file"""
    try:
        with open(BACKUP_STATE_FILE, "r") as f:
            state = json.load(f)
            return datetime.fromisoformat(state.get("last_backup_utc"))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return None


def set_last_backup_time(dt):
    """Save the timestamp of the last backup to state file"""
    state = {"last_backup_utc": dt.isoformat()}
    with open(BACKUP_STATE_FILE, "w") as f:
        json.dump(state, f)


def should_backup_now():
    """Check if it's time to backup (6 hours since last backup)"""
    last_backup = get_last_backup_time()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if last_backup is None:
        # First backup ever
        return True

    time_since_last = now - last_backup
    return time_since_last >= timedelta(hours=BACKUP_INTERVAL_HOURS)


def create_backup():
    """Create a timestamped backup of the database"""
    ensure_backup_dir()

    if not DB_PATH.exists():
        logger.warning(f"Database not found at {DB_PATH}")
        return False

    try:
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"sports_intel_backup_{timestamp}.db"

        # Use sqlite3 to create a backup
        conn = sqlite3.connect(str(DB_PATH))
        backup_conn = sqlite3.connect(str(backup_path))

        with backup_conn:
            conn.backup(backup_conn)

        backup_conn.close()
        conn.close()

        logger.info(f"✓ Backup created: {backup_path.name}")

        # Update last backup time
        set_last_backup_time(datetime.now(timezone.utc).replace(tzinfo=None))

        # Clean up old backups (keep last 48 hours worth = 8 backups)
        cleanup_old_backups()

        return True

    except Exception as e:
        logger.exception(f"✗ Backup failed: {e}")
        return False


def cleanup_old_backups(keep_count=8):
    """Remove old backups, keeping only the most recent ones"""
    try:
        backup_files = sorted(BACKUP_DIR.glob("sports_intel_backup_*.db"))

        if len(backup_files) > keep_count:
            for old_backup in backup_files[:-keep_count]:
                old_backup.unlink()
                logger.info(f"Cleaned up old backup: {old_backup.name}")

    except Exception as e:
        logger.warning(f"Backup cleanup error: {e}")


async def backup_job():
    """Async job to check and run backups"""
    if should_backup_now():
        return create_backup()
    return False


def init_backup_logging():
    """Initialize logging for backup service"""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] DB_BACKUP: %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


if __name__ == "__main__":
    # Test the backup
    init_backup_logging()
    logger.info("Starting database backup test...")
    success = create_backup()
    if success:
        logger.info("Backup test completed successfully")
        next_backup = get_last_backup_time() + timedelta(hours=BACKUP_INTERVAL_HOURS)
        logger.info(f"Next scheduled backup: {next_backup}")
    else:
        logger.error("Backup test failed")
