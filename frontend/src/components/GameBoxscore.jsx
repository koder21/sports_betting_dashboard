import React from 'react';
import './GameBoxscore.css';

const GameBoxscore = ({ gameData }) => {
  // Parse the metadata
  const metadata = typeof gameData.metadata === 'string' 
    ? JSON.parse(gameData.metadata) 
    : gameData.metadata;

  const { home_team, away_team, home_score, away_score, sport, status } = metadata;

  return (
    <div className="game-boxscore">
      <div className="boxscore-header">
        <span className="sport-badge">{sport?.toUpperCase() || 'GAME'}</span>
        <span className="status-badge">{status || 'FINAL'}</span>
      </div>
      
      <div className="boxscore-content">
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
      
      <div className="boxscore-footer">
        <span className="game-time">
          {new Date(gameData.created_at).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
          })}
        </span>
      </div>
    </div>
  );
};

export default GameBoxscore;
