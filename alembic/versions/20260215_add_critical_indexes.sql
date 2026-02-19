-- Phase 1: Critical Performance Indexes Migration
-- Run these SQL statements in your PostgreSQL database

-- bet.py indexes
CREATE INDEX IF NOT EXISTS ix_bets_sport_id ON bets(sport_id);
CREATE INDEX IF NOT EXISTS ix_bets_game_id ON bets(game_id);
CREATE INDEX IF NOT EXISTS ix_bets_player_id ON bets(player_id);
CREATE INDEX IF NOT EXISTS ix_bets_parlay_id ON bets(parlay_id);
CREATE INDEX IF NOT EXISTS ix_bets_status ON bets(status);
CREATE INDEX IF NOT EXISTS ix_bets_sport_status ON bets(sport_id, status);
CREATE INDEX IF NOT EXISTS ix_bets_game_status ON bets(game_id, status);

-- player_stats.py indexes
CREATE INDEX IF NOT EXISTS ix_player_stats_game_id ON player_stats(game_id);
CREATE INDEX IF NOT EXISTS ix_player_stats_player_id ON player_stats(player_id);
CREATE INDEX IF NOT EXISTS ix_player_stats_team_id ON player_stats(team_id);
CREATE INDEX IF NOT EXISTS ix_player_stats_sport ON player_stats(sport);
CREATE UNIQUE INDEX IF NOT EXISTS uq_player_stats_game_player ON player_stats(game_id, player_id);

-- injury.py indexes
CREATE INDEX IF NOT EXISTS ix_injuries_player_id ON injuries(player_id);
CREATE INDEX IF NOT EXISTS ix_injuries_team_id ON injuries(team_id);

-- standing.py indexes
CREATE INDEX IF NOT EXISTS ix_standings_team_id ON standings(team_id);
CREATE INDEX IF NOT EXISTS ix_standings_season_year ON standings(season_year);
