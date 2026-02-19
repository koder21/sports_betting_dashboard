-- Phase 2: Data Integrity Unique Constraints Migration
-- Run these SQL statements in your PostgreSQL database

-- player_stats.py - prevent duplicate stats
ALTER TABLE player_stats
ADD CONSTRAINT uq_player_stats_game_player
UNIQUE (game_id, player_id);

-- standing.py - prevent duplicate standings
ALTER TABLE standings
ADD CONSTRAINT uq_standing_team_season
UNIQUE (team_id, season_year);

-- injury.py - prevent duplicate injuries
ALTER TABLE injuries
ADD CONSTRAINT uq_injury_player_team_desc
UNIQUE (player_id, team_id, description);
