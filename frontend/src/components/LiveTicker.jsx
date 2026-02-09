import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function LiveTicker() {
  const [games, setGames] = useState([]);
  const navigate = useNavigate();

  const loadLive = async () => {
    try {
        const res = await api.get("/live");
        let list = res.data || [];

        // SMART ORDERING: live > final (results) > scheduled (upcoming)
        list.sort((a, b) => {
        const statusRank = (g) => {
            if (g.status === "in") return 0;
            if (g.status === "final") return 1;
            if (g.status === "scheduled") return 2;
            return 3;
        };

        const rankA = statusRank(a);
        const rankB = statusRank(b);
        if (rankA !== rankB) return rankA - rankB;

        const diffA = Math.abs((a.home_score || 0) - (a.away_score || 0));
        const diffB = Math.abs((b.home_score || 0) - (b.away_score || 0));

        if (rankA === 0) {
            if (diffA !== diffB) return diffA - diffB;
            return (a.clock || "").localeCompare(b.clock || "");
        }

        if (rankA === 1) {
            return (a.start_time || "").localeCompare(b.start_time || "");
        }

        if (rankA === 2) {
            if (diffA !== diffB) return diffA - diffB;
        }

        return String(a.game_id).localeCompare(String(b.game_id));
        });

        setGames(list);
    } catch (err) {
        console.error("Ticker failed to load live scores:", err);
    }
  };

  useEffect(() => {
    loadLive();
    // Poll more frequently (every 10 seconds instead of 15) for faster status updates
    const interval = setInterval(loadLive, 10000);
    return () => clearInterval(interval);
  }, []);

  const sportIcon = (sport) => {
    switch (sport) {
      case "NBA": return "🏀";
      case "NFL": return "🏈";
      case "NHL": return "🏒";
      case "NCAAB": return "🎓🏀";
      case "EPL": return "⚽";
      default: return "🎮";
    }
  };

  const formatGameTime = (game) => {
    // For live games, show clock
    if (game.status === "in" && game.clock) {
      return <span className="clock">({game.clock})</span>;
    }
    // For scheduled/upcoming games, show start time (EST)
    if (game.status === "scheduled" && game.start_time) {
      return <span className="start-time">{game.start_time}</span>;
    }
    // For finished games, show final
    if (game.status === "final") {
      return <span className="final-badge">FINAL</span>;
    }
    return null;
  };

  if (games.length === 0) {
    return (
      <div className="ticker-bar empty">
        No live games right now
      </div>
    );
  }

  return (
    <div className="ticker-bar">
      <div className="ticker-wrapper">
        <div className="ticker-scroll">
          {games.map((g) => (
            <span
              key={`game-${g.game_id}-${g.status}`}
              className={`ticker-item ${g.status}`}
              onClick={() => navigate(`/games/${g.game_id}`)}
            >
              <span className="sport-icon">{sportIcon(g.sport)}</span>

              {g.home_logo && (
                <img src={g.home_logo} className="team-logo" alt="" />
              )}
              {g.home_team} <span className="score">{g.home_score}</span>

              <span className="vs">vs</span>

              {g.away_logo && (
                <img src={g.away_logo} className="team-logo" alt="" />
              )}
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
              onClick={() => navigate(`/games/${g.game_id}`)}
            >
              <span className="sport-icon">{sportIcon(g.sport)}</span>

              {g.home_logo && (
                <img src={g.home_logo} className="team-logo" alt="" />
              )}
              {g.home_team} <span className="score">{g.home_score}</span>

              <span className="vs">vs</span>

              {g.away_logo && (
                <img src={g.away_logo} className="team-logo" alt="" />
              )}
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
          animation: ticker-scroll 60s linear infinite;
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
            animation: ticker-scroll 80s linear infinite;
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
