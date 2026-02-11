# Project Structure

## Clean & Organized

### Root Directory
- **Core Files**
  - `alembic.ini` - Database migration configuration
  - `sports_intel.db` - SQLite database
  - `run.sh` - Server startup script
  - `sports_betting_dashboard.code-workspace` - VS Code workspace config

- **Documentation** (See `DOCUMENTATION_INDEX.md`)
  - Primary: `BETTING_TRACKER_README.md`, `TIMEZONE_QUICK_START.md`, `LATEST_UPDATES.md`
  - Reference: `EXTERNAL_MODELS_README.md`, `ARCHITECTURE_VISUAL.md`
  - Legacy: Other `*.md` files (consolidated in index)

### `backend/` - Python/FastAPI

```
backend/
├── main.py                    # FastAPI app initialization, scheduler startup
├── config.py                  # Environment configuration
├── db.py                       # Database session management
│
├── models/                     # SQLAlchemy ORM models
│   ├── base.py               # Base model class
│   ├── game.py               # Game records
│   ├── games_results.py       # Completed games
│   ├── games_upcoming.py       # Scheduled games
│   ├── games_live.py         # Real-time game data
│   ├── team.py               # Team information
│   ├── player.py             # Player profiles
│   ├── player_stats.py        # Player performance stats
│   ├── bet.py                # User bets
│   ├── sport.py              # Sport definitions
│   ├── standing.py           # League standings
│   ├── alert.py              # User alerts
│   └── injury.py             # Player injuries
│
├── routers/                    # FastAPI route handlers
│   ├── health.py             # Server health check
│   ├── live.py               # Live scores endpoint
│   ├── games.py              # Game data endpoints
│   ├── bets.py               # Betting endpoints
│   ├── props.py              # Player prop endpoints
│   ├── analytics.py          # Analytics endpoints
│   ├── alerts.py             # Alert management
│   ├── sports_analytics.py    # Sports stats endpoints
│   ├── aai_bets.py           # AAI betting recommendations
│   └── scraping.py           # Data scraping triggers
│
├── services/                   # Business logic
│   ├── aai/                  # Betting recommendation engine
│   │   ├── recommendations.py        # AAIBetRecommender, ExternalOddsAggregator
│   │   ├── EXTERNAL_MODELS_GUIDE.md # Integration guide
│   │   └── EXAMPLE_MODELS.py        # Code examples
│   │
│   ├── scraping/             # ESPN data collection
│   │   ├── base.py           # Base scraper class
│   │   ├── nba.py, nfl.py, etc.   # Sport-specific scrapers
│   │   └── common_team_league.py   # Shared utilities
│   │
│   ├── intelligence/         # Game analysis
│   │   ├── game_intel.py    # Game-level insights
│   │   └── prop_intel.py    # Player prop analysis
│   │
│   ├── betting/              # Bet tracking & grading
│   │   ├── engine.py        # Bet processing
│   │   └── grader.py        # Outcome evaluation
│   │
│   ├── alerts/               # Notification system
│   │   └── manager.py       # Alert creation & delivery
│   │
│   ├── espn_client.py        # ESPN API wrapper
│   ├── scraper_nba.py, etc.  # Legacy scraper files (kept for compatibility)
│   └── caching.py            # Response caching utilities
│
├── scheduler/                  # Background task runner
│   ├── tasks.py              # Scheduled jobs (scraping, live updates, grading)
│   └── write_queue.py        # Async database write buffering
│
├── repositories/              # Data access layer
│   ├── base.py               # Base repository class
│   ├── *_repo.py             # Entity-specific repos (bets, teams, players, etc.)
│   └── *.py                  # Query builders for common operations
│
├── utils/                      # Utility functions
│   ├── time.py               # Timezone & time utilities
│   ├── log.py                # Logging configuration
│   ├── errors.py             # Custom exceptions
│   └── json.py               # JSON serialization helpers
│
├── websocket/                  # Real-time updates (prepared but not yet active)
│   ├── manager.py            # WebSocket connection management
│   └── __init__.py
│
└── __init__.py
```

### `frontend/` - React/Vite

```
frontend/
├── package.json              # Node.js dependencies
├── vite.config.js            # Build configuration
├── index.html                # HTML entry point
│
├── src/
│   ├── App.jsx               # Main router component
│   ├── main.jsx              # React entry point
│   │
│   ├── pages/                # Full page components
│   │   ├── LiveScoresPage.jsx           # Live game scores
│   │   ├── AAIBetsPage.jsx              # AI betting recommendations
│   │   ├── BetsPage.jsx                 # Bet tracking & history
│   │   ├── PropExplorerPage.jsx         # Player props browser
│   │   ├── GameIntelPage.jsx            # Game detail view
│   │   ├── AnalyticsPage.jsx            # Betting analytics
│   │   ├── SportsAnalyticsPage.jsx      # Sports statistics
│   │   ├── AlertsPage.jsx               # Alert management
│   │   ├── SettingsPage.jsx             # User settings (timezone)
│   │   └── *Page.css                    # Page-specific styles
│   │
│   ├── components/           # Reusable UI components
│   │   ├── Layout.jsx        # Main layout wrapper with sidebar
│   │   ├── LiveTicker.jsx    # Scrolling game ticker
│   │   ├── AlertToasts.jsx   # Toast notifications
│   │   └── ...               # Other shared components
│   │
│   ├── services/             # API clients & utilities
│   │   ├── api.js            # Axios API instance
│   │   └── timezoneService.js # Timezone conversion (localStorage-based)
│   │
│   └── styles/               # Global styles (if any)
│
├── public/                    # Static assets
└── dist/                      # Build output (created by vite build)
```

### `alembic/` - Database Migrations

```
alembic/
├── env.py                    # Migration environment setup
└── versions/                 # Versioned migrations
    ├── 0001_*.py            # Initial schema
    ├── 0002_*.py            # Data type conversions
    └── ...                  # Further migrations
```

---

## Key Design Decisions

### Separation of Concerns
- **Models**: Define schema only (no business logic)
- **Repositories**: Data access layer (queries)
- **Services**: Business logic & external integrations
- **Routers**: HTTP interface, request/response handling

### Timezone Handling
- Database: Stores all times in UTC
- API: Returns ISO 8601 UTC strings
- Frontend: Uses `timezoneService.js` for client-side conversion
- User Setting: Stored in localStorage, never affects database

### Betting Recommendations (AAI)
- Form Analysis: Last 5 games or 90 days (recent team performance)
- External Models: Vegas, Elo, ML, Kelly (aggregated as mean)
- Confidence Blending: 50% form confidence + 50% external mean
- Parlay Generation: All combinations of sizes 2, 3, 4, 5, 7, 12 leg
- Display: Top 5 recommendations per size

### Data Flow
```
ESPN API → Scheduler → Database
                      ↓
                   Repositories
                      ↓
           Services (Intelligence, Betting, etc.)
                      ↓
                   Routers (HTTP endpoints)
                      ↓
                   Frontend (React)
                      ↓
                   Browser (with timezone conversion)
```

---

## Active Features

✅ **Live Scores** - Real-time game updates from ESPN  
✅ **AAI Betting** - Data-driven recommendations with model aggregation  
✅ **Bet Tracking** - Log, grade, and analyze bets  
✅ **Player Props** - Browse player performance predictions  
✅ **Timezone Settings** - Convert all times to user's timezone  
✅ **Alerts** - Notifications for games and bet outcomes  
✅ **Analytics** - Betting performance metrics  

---

## Development Notes

### Adding a Feature
1. Create model in `backend/models/`
2. Create repository in `backend/repositories/` (if needed)
3. Implement service logic in `backend/services/`
4. Add HTTP endpoint in `backend/routers/`
5. Build React component in `frontend/src/pages/`
6. Wire up in `frontend/src/App.jsx`

### Running Locally
```bash
# Backend
cd backend && python -m uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend && npm run dev
```

### Database
Migrations are handled by Alembic. Run with:
```bash
alembic upgrade head
```

### Scheduler
The task scheduler runs automatically when the backend starts. Key tasks:
- Scrape ESPN data every 5 minutes
- Update live game scores
- Grade completed bets
- Send alerts

