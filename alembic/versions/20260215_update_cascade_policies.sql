-- Phase 3: Cascade Policies Migration
-- Run these SQL statements in your PostgreSQL database

-- bet.py - Add cascade policies
ALTER TABLE bets
DROP CONSTRAINT IF EXISTS bets_sport_id_fkey,
ADD CONSTRAINT bets_sport_id_fkey
FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE CASCADE;

ALTER TABLE bets
DROP CONSTRAINT IF EXISTS bets_game_id_fkey,
ADD CONSTRAINT bets_game_id_fkey
FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE SET NULL;

-- player_stats.py - Add cascade policies
ALTER TABLE player_stats
DROP CONSTRAINT IF EXISTS player_stats_game_id_fkey,
ADD CONSTRAINT player_stats_game_id_fkey
FOREIGN KEY (game_id) REFERENCES games_results(game_id) ON DELETE CASCADE;
