# How to recreate database tables

Use these steps when the schema has changed (e.g. after merging backends or changing models) so that tables match the current code.

---

## Option A: Recreate from the running app (recommended)

1. **Stop the backend** if it’s running (Ctrl+C the process that runs `uvicorn backend.main:app` or `./run.sh`).

2. **Back up the current DB** (optional, if you care about data):
   ```bash
   cp sports_intel.db sports_intel.db.bak
   ```
   Or from project root:
   ```bash
   cp backend/sports_intel.db backend/sports_intel.db.bak
   ```
   (The file may live in the backend folder or project root depending on how the app is run.)

3. **Delete the existing DB file** so it can be recreated from scratch:
   - If your config uses `sqlite+aiosqlite:///./sports_intel.db` (relative path), the file is created in the **current working directory** when the app runs. That’s usually project root if you run `uvicorn` from there, or `backend/` if you run from there.
   - Find and remove it, for example:
     ```bash
     rm -f sports_intel.db
     rm -f backend/sports_intel.db
     ```

4. **Start the backend again** so `init_db()` runs on startup and creates all tables:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   Or:
   ```bash
   ./run.sh
   ```

5. Tables are created on first request/startup. You can confirm with:
   ```bash
   sqlite3 sports_intel.db ".tables"
   ```
   (or `sqlite3 backend/sports_intel.db ".tables"` if the file is under `backend/`).

---

## Option B: Recreate from a one-off script

1. **Stop the backend** (same as above).

2. **Back up and/or delete the DB file** (same as steps 2–3 in Option A).

3. From the **project root**, run a script that imports all models and then calls `init_db()`:
   ```bash
   cd /path/to/sports_betting_dashboard
   python3 -c "
   import asyncio
   from backend.models import *   # register all models with Base.metadata
   from backend.db import init_db

   async def main():
       await init_db()
       print('Tables created.')

   asyncio.run(main())
   "
   ```

4. Start the backend as usual; it will use the new DB.

---

## Option C: Recreate using the shell script (no backup)

From project root:

```bash
# 1) Remove existing DB (adjust path if your DB lives elsewhere)
rm -f sports_intel.db backend/sports_intel.db

# 2) Start backend so init_db() runs and creates tables
uvicorn backend.main:app --reload --port 8000
# Stop with Ctrl+C after you see "Application startup complete" and tables exist, or leave it running.
```

---

## Where is the DB file?

- **Config default:** `backend/config.py` sets `DATABASE_URL = "sqlite+aiosqlite:///./sports_intel.db"`.
- The `./` means “current working directory” when the process starts. So:
  - Running `uvicorn backend.main:app` from **project root** → `sports_intel.db` in project root.
  - Running from `backend/` → `sports_intel.db` in `backend/`.
- You may also have an older `sports.db` in the repo; the app uses `sports_intel.db` unless you override `DATABASE_URL` in `.env`.

---

## Summary (minimal steps)

1. Stop the backend.
2. `rm -f sports_intel.db backend/sports_intel.db` (and back up first if you need the data).
3. Start the backend again (`uvicorn backend.main:app --reload --port 8000` or `./run.sh`).
4. Tables are created automatically on startup.
