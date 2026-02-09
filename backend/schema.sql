PRAGMA foreign_keys = ON;

------------------------------------------------------------
-- 1. TEAMS
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    name TEXT,
    abbreviation TEXT,
    sport TEXT,
    league TEXT,
    logo TEXT,
    color_primary TEXT,
    color_secondary TEXT,
    stadium TEXT,
    conference TEXT,
    division TEXT
);

------------------------------------------------------------
-- 2. PLAYERS
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    full_name TEXT,
    team_id TEXT,
    position TEXT,
    sport TEXT,
    league TEXT,
    headshot TEXT,
    jersey TEXT,
    height TEXT,
    weight TEXT,
    birthdate TEXT,
    nationality TEXT,
    active BOOLEAN,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

------------------------------------------------------------
-- 3. UPCOMING GAMES
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS games_upcoming (
    game_id TEXT PRIMARY KEY,
    sport TEXT,
    league TEXT,
    season TEXT,
    season_type TEXT,
    week INTEGER,
    round INTEGER,
    start_time TEXT,
    venue TEXT,
    broadcast TEXT,
    weather TEXT,
    neutral_site BOOLEAN,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team TEXT,
    away_team TEXT,
    home_logo TEXT,
    away_logo TEXT,
    odds_home REAL,
    odds_away REAL,
    spread_home REAL,
    spread_away REAL,
    total REAL,
    scraped_at TEXT,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

------------------------------------------------------------
-- 4. LIVE GAMES (OPTIONAL BUT RECOMMENDED)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS games_live (
    game_id TEXT PRIMARY KEY,
    sport TEXT,
    league TEXT,
    home_score INTEGER,
    away_score INTEGER,
    clock TEXT,
    period TEXT,
    possession TEXT,
    status TEXT,
    updated_at TEXT,
    FOREIGN KEY (game_id) REFERENCES games_upcoming(game_id)
);

------------------------------------------------------------
-- 5. RESULTS (FINISHED GAMES)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS games_results (
    game_id TEXT PRIMARY KEY,
    sport TEXT,
    league TEXT,
    season TEXT,
    season_type TEXT,
    week INTEGER,
    round INTEGER,
    start_time TEXT,
    end_time TEXT,
    venue TEXT,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team TEXT,
    away_team TEXT,
    home_logo TEXT,
    away_logo TEXT,
    home_score INTEGER,
    away_score INTEGER,
    status TEXT,
    attendance INTEGER,
    referees TEXT,
    weather TEXT,
    moved_at TEXT,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

------------------------------------------------------------
-- 6. PLAYER STATS (ALL SPORTS)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT,
    player_id TEXT,
    team_id TEXT,
    sport TEXT,
    league TEXT,

    -- Universal
    minutes TEXT,
    fantasy_points REAL,

    -- Basketball (NBA/NCAAB)
    points INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    fouls INTEGER,
    fg TEXT,
    three_pt TEXT,
    ft TEXT,

    -- Football (NFL/NCAAF)
    passing_yards INTEGER,
    passing_tds INTEGER,
    interceptions INTEGER,
    rushing_yards INTEGER,
    rushing_tds INTEGER,
    receiving_yards INTEGER,
    receiving_tds INTEGER,
    tackles INTEGER,
    sacks INTEGER,
    forced_fumbles INTEGER,

    -- Baseball (MLB)
    hits INTEGER,
    runs INTEGER,
    rbi INTEGER,
    hr INTEGER,
    sb INTEGER,
    bb INTEGER,
    so INTEGER,
    pitch_ip TEXT,
    pitch_k INTEGER,
    pitch_bb INTEGER,
    pitch_er INTEGER,

    -- Hockey (NHL)
    nhl_goals INTEGER,
    nhl_assists INTEGER,
    nhl_shots INTEGER,
    nhl_hits INTEGER,
    nhl_blocks INTEGER,
    nhl_plus_minus INTEGER,
    goalie_saves INTEGER,
    goalie_ga INTEGER,
    goalie_sv_pct REAL,

    -- Soccer (EPL)
    epl_goals INTEGER,
    epl_assists INTEGER,
    epl_shots_on_target INTEGER,
    epl_passes INTEGER,
    epl_tackles INTEGER,
    epl_saves INTEGER,

    -- UFC
    strikes_landed INTEGER,
    strikes_attempted INTEGER,
    takedowns_landed INTEGER,
    takedowns_attempted INTEGER,
    control_time TEXT,
    rounds_won INTEGER,

    scraped_at TEXT,

    FOREIGN KEY (game_id) REFERENCES games_results(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

------------------------------------------------------------
-- INDEXES (PERFORMANCE)
------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_upcoming_start_time ON games_upcoming(start_time);
CREATE INDEX IF NOT EXISTS idx_results_start_time ON games_results(start_time);
CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_stats(team_id);
