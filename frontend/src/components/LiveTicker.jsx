import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { convertToUserTimezone } from '../services/timezoneService';

function LiveTicker() {
  const [games, setGames] = useState([]);
  const navigate = useNavigate();

  // Fetch live games from API
  const loadLive = React.useCallback(async () => {
    try {
      const res = await api.get('/api/live');
      setGames(res.data || []);
    } catch {
      setGames([]);
    }
  }, []);

  useEffect(() => {
    loadLive();
    const interval = setInterval(loadLive, 10000);
    return () => clearInterval(interval);
  }, [loadLive]);

  const sportIcon = (sport) => {
    switch (sport) {
      case 'NBA':
        return '🏀';
      case 'NFL':
        return '🏈';
      case 'NHL':
        return '🏒';
      case 'NCAAB':
        return '🎓🏀';
      case 'EPL':
        return '⚽';
      default:
        return '🎮';
    }
  };

  const formatGameTime = (game) => {
    // For live games, show clock
    if (game.status === 'in' && game.clock) {
      return <span className="clock">({game.clock})</span>;
    }
    // For scheduled/upcoming games, show start time in user's timezone
    if (game.status === 'scheduled' && game.start_time) {
      // Use timezone conversion
      return (
        <span className="start-time">{convertToUserTimezone(game.start_time, 'time-with-tz')}</span>
      );
    }
    // For finished games, show final
    if (game.status === 'final') {
      return <span className="final-badge">FINAL</span>;
    }
    return null;
  };

  if (games.length === 0) {
    return <div className="ticker-bar empty">No live games right now</div>;
  }

  return (
    <div className="ticker-bar">
      <div className="ticker-wrapper">
        <div className="ticker-scroll">
          {games.map((g) => (
            <span
              key={`game-${g.game_id}-${g.status}`}
              className={`ticker-item ${g.status}`}
              onClick={() => navigate(`/games/${g.game_id}/details`)}
            >
              <span className="sport-icon">{sportIcon(g.sport)}</span>
              <img
                src={g.home_logo || '/images/default_team_logo.png'}
                className="team-logo"
                alt=""
                onError={e => {
                  if (e.target.src.indexOf('default_team_logo.png') === -1) {
                    e.target.onerror = null;
                    e.target.src = '/images/default_team_logo.png';
                  }
                }}
              />
              {g.home_team} <span className="score">{g.home_score}</span>
              <span className="vs">vs</span>
              <img
                src={g.away_logo || '/images/default_team_logo.png'}
                className="team-logo"
                alt=""
                onError={e => {
                  if (e.target.src.indexOf('default_team_logo.png') === -1) {
                    e.target.onerror = null;
                    e.target.src = '/images/default_team_logo.png';
                  }
                }}
              />
              {g.away_team} <span className="score">{g.away_score}</span>
              {formatGameTime(g)}
            </span>
          ))}
        </div>
        <div className="ticker-scroll">
          {games.map((g) => (
            <span
              key={`game-dup-${g.game_id}-${g.status}`}
              className={`ticker-item ${g.status}`}
              onClick={() => navigate(`/games/${g.game_id}/details`)}
            >
              <span className="sport-icon">{sportIcon(g.sport)}</span>
              <img
                src={g.home_logo || '/images/default_team_logo.png'}
                className="team-logo"
                alt=""
                onError={e => {
                  if (e.target.src.indexOf('default_team_logo.png') === -1) {
                    e.target.onerror = null;
                    e.target.src = '/images/default_team_logo.png';
                  }
                }}
              />
              {g.home_team} <span className="score">{g.home_score}</span>
              <span className="vs">vs</span>
              <img
                src={g.away_logo || '/images/default_team_logo.png'}
                className="team-logo"
                alt=""
                onError={e => {
                  if (e.target.src.indexOf('default_team_logo.png') === -1) {
                    e.target.onerror = null;
                    e.target.src = '/images/default_team_logo.png';
                  }
                }}
              />
              {g.away_team} <span className="score">{g.away_score}</span>
              {formatGameTime(g)}
            </span>
          ))}
        </div>
      </div>

      <style>{`
        .ticker-bar {
          width: 100%;
          background: #0d0d0d;
          color: #fff;
          padding: 3px 0;
          border-bottom: 1px solid #222;
          font-size: 0.8rem;
          position: sticky;
          top: 0;
          z-index: 999;
          height: 28px;
          display: flex;
          align-items: center;
          overflow: hidden;
        }

        .ticker-bar.empty {
          text-align: center;
          opacity: 0.7;
          font-size: 0.8rem;
        }

        .ticker-wrapper {
          position: relative;
          width: 100%;
          height: 100%;
          overflow: hidden;
          mask-image: linear-gradient(to right, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 10%, rgba(0,0,0,1) 90%, rgba(0,0,0,0) 100%);
          -webkit-mask-image: linear-gradient(to right, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 10%, rgba(0,0,0,1) 90%, rgba(0,0,0,0) 100%);
        }

        .ticker-scroll {
          position: absolute;
          top: 0;
          left: 0;
          display: flex;
          gap: 35px;
          padding: 0 35px;
          animation: ticker-scroll 120s linear infinite;
          white-space: nowrap;
          height: 100%;
          align-items: center;
        }

        .ticker-bar:hover .ticker-scroll {
          animation-play-state: paused;
        }

        .ticker-item {
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 3px;
          flex-shrink: 0;
        }

        .ticker-item:hover {
          text-decoration: underline;
        }

        .team-logo {
          width: 14px;
          height: 14px;
          border-radius: 50%;
        }

        .sport-icon {
          opacity: 0.8;
          font-size: 0.85rem;
        }

        .vs {
          opacity: 0.5;
          margin: 0 2px;
          font-size: 0.7rem;
        }

        .clock {
          opacity: 0.7;
          margin-left: 2px;
          font-size: 0.75rem;
        }

        .final-badge {
          font-size: 0.7rem;
          background: #c62828;
          color: #fff;
          padding: 2px 6px;
          border-radius: 3px;
          font-weight: 700;
          margin-left: 2px;
        }

        .start-time {
          opacity: 1;
          margin-left: 4px;
          font-size: 0.8rem;
          font-weight: 600;
          color: #ffeb3b;
          background: rgba(255, 235, 59, 0.1);
          padding: 2px 4px;
          border-radius: 2px;
        }

        .score {
          background: #fff;
          color: #000;
          padding: 1px 4px;
          border-radius: 3px;
          font-weight: 600;
          margin: 0 2px;
        }

        /* Color coding */
        .ticker-item.in { color: #00e676 !important; }
        .ticker-item.final { color: #ff5252 !important; }
        .ticker-item.scheduled { color: #ffeb3b !important; }

        @keyframes ticker-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }

        /* Mobile */
        @media (max-width: 600px) {
          .ticker-bar {
            font-size: 0.7rem;
            padding: 2px 0;
            height: 24px;
          }
          .ticker-item {
            gap: 2px;
          }
          .ticker-scroll {
            gap: 30px;
            padding: 0 30px;
            animation: ticker-scroll 160s linear infinite;
          }
          .team-logo {
            width: 12px;
            height: 12px;
          }
        }
      `}</style>
    </div>
  );
}

export default LiveTicker;
