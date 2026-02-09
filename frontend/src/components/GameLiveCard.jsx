import React from 'react';
import './GameLiveCard.css';

const GameLiveCard = ({ gameData }) => {
  // Parse the metadata
  const metadata = typeof gameData.metadata === 'string' 
    ? JSON.parse(gameData.metadata) 
    : gameData.metadata;

  const { 
    home_team, 
    away_team, 
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
            <span className="team-name">{away_team || 'Away Team'}</span>
          </div>
          <div className="team-score">{away_score || 0}</div>
        </div>
        
        <div className="score-divider">@</div>
        
        <div className="team-row">
          <div className="team-info">
            <span className="team-name home">{home_team || 'Home Team'}</span>
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
