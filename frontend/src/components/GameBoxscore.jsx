import React from 'react';
import './GameBoxscore.css';

const GameBoxscore = ({ gameData }) => {
  // Parse the metadata with error handling
  let metadata;
  let parseError = false;
  if (typeof gameData.metadata === 'string') {
    try {
      metadata = JSON.parse(gameData.metadata);
    } catch {
      parseError = true;
      metadata = {};
    }
  } else {
    metadata = gameData.metadata || {};
  }

  // Prefer home_team_name/away_team_name if available
  const homeTeam = metadata.home_team_name || metadata.home_team || 'Home Team';
  const awayTeam = metadata.away_team_name || metadata.away_team || 'Away Team';
  const { home_score, away_score, sport, status } = metadata;

  if (parseError) {
    return (
      <div className="game-boxscore error">
        <div className="boxscore-header">
          <span className="sport-badge">GAME</span>
          <span className="status-badge">ERROR</span>
        </div>
        <div className="boxscore-content">
          <div className="error-message">Invalid game metadata (not valid JSON)</div>
        </div>
      </div>
    );
  }
  return (
    <div className="game-boxscore">
      <div className="boxscore-header">
        <span className="sport-badge">{sport?.toUpperCase() || 'GAME'}</span>
        <span className="status-badge">{status || 'FINAL'}</span>
      </div>

      <div className="boxscore-content">
        <div className="team-row">
          <div className="team-info">
            <span className="team-name">{awayTeam}</span>
          </div>
          <div className="team-score">{away_score || 0}</div>
        </div>
        <div className="score-divider">@</div>
        <div className="team-row">
          <div className="team-info">
            <span className="team-name home">{homeTeam}</span>
          </div>
          <div className="team-score">{home_score || 0}</div>
        </div>
      </div>

      <div className="boxscore-footer">
        <span className="game-time">
          {new Date(gameData.created_at).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
          })}
        </span>
      </div>
    </div>
  );
};

export default GameBoxscore;
