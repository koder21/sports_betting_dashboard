import os
import subprocess
from datetime import datetime, timedelta

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '../../backups')
BACKUP_FILE_PREFIX = 'postgres_backup'
LAST_BACKUP_FILE = os.path.join(BACKUP_DIR, 'last_backup.txt')

DB_NAME = os.environ.get('POSTGRES_DB')
DB_USER = os.environ.get('POSTGRES_USER')
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_PORT = os.environ.get('POSTGRES_PORT', '5432')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD')


def get_last_backup_time():
    if not os.path.exists(LAST_BACKUP_FILE):
        return None
    with open(LAST_BACKUP_FILE, 'r') as f:
        ts = f.read().strip()
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None


def set_last_backup_time(dt):
    with open(LAST_BACKUP_FILE, 'w') as f:
        f.write(dt.isoformat())


def perform_backup():
    if not DB_NAME or not DB_USER or not DB_PASSWORD:
        print("Backup skipped: POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD env vars must be set.")
        return

    now = datetime.now()
    backup_filename = f"{BACKUP_FILE_PREFIX}_{now.strftime('%Y%m%d_%H%M%S')}.sql"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    cmd = [
        'pg_dump',
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-U', DB_USER,
        '-F', 'c',
        '-b',
        '-v',
        '-f', backup_path,
        DB_NAME
    ]
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASSWORD
    try:
        subprocess.run(cmd, check=True, env=env)
        set_last_backup_time(now)
        print(f"Backup completed: {backup_path}")
    except Exception as e:
        print(f"Backup failed: {e}")


def should_backup():
    last = get_last_backup_time()
    if not last:
        return True
    return datetime.now() - last > timedelta(hours=24)


if __name__ == '__main__':
    if should_backup():
        perform_backup()
    else:
        print("No backup needed.")
