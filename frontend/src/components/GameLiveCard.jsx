import React from 'react';
import './GameLiveCard.css';

const GameLiveCard = ({ gameData }) => {
  // Parse the metadata
  const metadata = typeof gameData.metadata === 'string' 
    ? JSON.parse(gameData.metadata) 
    : gameData.metadata;

  // Prefer home_team_name/away_team_name if available
  const homeTeam = metadata.home_team_name || metadata.home_team || 'Home Team';
  const awayTeam = metadata.away_team_name || metadata.away_team || 'Away Team';
  const { 
    home_score, 
    away_score, 
    sport, 
    status,
    period,
    clock 
  } = metadata;

  return (
    <div className="game-live-card">
      <div className="live-header">
        <span className="sport-badge">{sport?.toUpperCase() || 'GAME'}</span>
        <span className="live-badge pulsing">
          <span className="live-dot"></span>
          LIVE
        </span>
      </div>
      
      <div className="live-content">
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
      
      <div className="live-footer">
        {period && clock && (
          <div className="game-clock">
            <span className="period">{period}</span>
            <span className="clock">{clock}</span>
          </div>
        )}
        {status && !clock && (
          <div className="game-status">{status}</div>
        )}
      </div>
    </div>
  );
};

export default GameLiveCard;
