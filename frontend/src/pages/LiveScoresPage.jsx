import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function LiveScoresPage() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [pendingBetsByGame, setPendingBetsByGame] = useState({});
  const prevScores = useRef({});
  const navigate = useNavigate();

  const estimateWinProb = (g) => {
    // Very rough heuristic: only for NBA/NFL for now
    if (!g || !g.status) return null;
    if (g.status === "final") {
      if (g.home_score > g.away_score) return { home: 0.99, away: 0.01 };
      if (g.home_score < g.away_score) return { home: 0.01, away: 0.99 };
      return { home: 0.5, away: 0.5 };
    }

    const home = Number(g.home_score || 0);
    const away = Number(g.away_score || 0);
    const diff = home - away;

    // If no score yet, call it 50/50
    if (home === 0 && away === 0) return { home: 0.5, away: 0.5 };

    // Use period + clock to weight confidence a bit
    const period = Number(g.period || 1);
    const lateGameFactor = Math.min(period / 4, 1); // crude

    const base = 0.5 + Math.tanh(diff / 10) * 0.25 * lateGameFactor;
    const homeProb = Math.max(0.01, Math.min(0.99, base));
    const awayProb = 1 - homeProb;

    return { home: homeProb, away: awayProb };
  };

  const buildPendingMap = (betsList) => {
    const map = {};
    betsList
      .filter((b) => (b.status === "pending" || b.status === "won" || b.status === "lost") && b.game_id)
      .forEach((b) => {
        if (!map[b.game_id]) {
          map[b.game_id] = { selections: [], players: [], finished: [] };
        }
        if (b.selection) {
          map[b.game_id].selections.push(String(b.selection).toLowerCase());
        }
        if (b.player_name) {
          map[b.game_id].players.push(b.player_name);
        }
        if (b.status === "won" || b.status === "lost") {
          const result = b.status === "won" ? "W" : "L";
          map[b.game_id].finished.push(result);
        }
      });
    return map;
  };

  const teamMatchesSelection = (teamName, selections) => {
    if (!teamName || !selections || selections.length === 0) return false;
    const teamTokens = String(teamName)
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 2);
    return selections.some((sel) => teamTokens.some((t) => sel.includes(t)));
  };

  const loadLive = async () => {
    try {
      const [liveRes, betsRes] = await Promise.all([
        api.get("/live"),
        api.get("/bets/all"),
      ]);
      const newGames = liveRes.data || [];
      const bets = betsRes?.data?.bets || [];
      setPendingBetsByGame(buildPendingMap(bets));

      newGames.forEach((g) => {
        const key = g.game_id;
        const prev = prevScores.current[key];

        if (prev) {
          g.homeScoreChanged = prev.home_score !== g.home_score;
          g.awayScoreChanged = prev.away_score !== g.away_score;
        }

        prevScores.current[key] = {
          home_score: g.home_score,
          away_score: g.away_score,
        };

        g.winProb = estimateWinProb(g);
      });

      setGames(newGames);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to load live scores:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLive();
    const interval = setInterval(loadLive, 15000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (date) => {
    if (!date) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const getStatusClass = (status) => {
    if (status === "in") return "status-live";
    if (status === "final") return "status-final";
    return "status-scheduled";
  };

  const formatProb = (p) =>
    p == null ? "-" : `${Math.round(p * 100)}%`;

  const liveGames = games.filter(g => g.status === "in");
  const finishedGames = games.filter(g => g.status === "final");
  const upcomingGames = games.filter(g => g.status === "scheduled");

  const renderGamesTable = (gamesList, title) => {
    if (gamesList.length === 0) return null;
    
    return (
      <div className="games-section">
        <h2 className="section-title">{title}</h2>
        <table className="table live-table">
          <thead>
            <tr>
              <th>Sport</th>
              <th>Matchup</th>
              <th>My Bets</th>
              <th>Score</th>
              <th>Clock</th>
              <th>Period</th>
              <th>Win Prob</th>
              <th>Game Start</th>
            </tr>
          </thead>
          <tbody>
            {gamesList.map((g) => (
              (() => {
                const pendingInfo = pendingBetsByGame[g.game_id];
                const selections = pendingInfo?.selections || [];
                const players = pendingInfo?.players || [];
                const finished = pendingInfo?.finished || [];
                const hasHomeBet = teamMatchesSelection(g.home_team, selections);
                const hasAwayBet = teamMatchesSelection(g.away_team, selections);
                const hasPlayerBet = players.length > 0;
                return (
              <tr
                key={g.game_id}
                className={`game-row ${getStatusClass(g.status)}`}
                onClick={() => navigate(`/games/${g.game_id}`)}>
                <td>{g.sport}</td>
                <td>{g.home_team} vs {g.away_team}</td>
                <td>
                  {!pendingInfo && <span className="bet-badge none">None</span>}
                  {pendingInfo && (
                    <div className="bet-badges">
                      {hasHomeBet && <span className="bet-badge home">Home</span>}
                      {hasAwayBet && <span className="bet-badge away">Away</span>}
                      {hasPlayerBet && (
                        <span
                          className="bet-badge player"
                          title={players.join(", ")}
                        >
                          Player ({players.length})
                        </span>
                      )}
                      {finished.length > 0 && (
                        <>
                          {finished.map((result, idx) => (
                            <span
                              key={idx}
                              className={`bet-badge ${result === "W" ? "win" : "loss"}`}
                            >
                              {result}
                            </span>
                          ))}
                        </>
                      )}
                    </div>
                  )}
                </td>

                <td>
                  <span
                    className={
                      g.homeScoreChanged ? "score flash" : "score"
                    }
                  >
                    {g.home_score}
                  </span>
                  {" - "}
                  <span
                    className={
                      g.awayScoreChanged ? "score flash" : "score"
                    }
                  >
                    {g.away_score}
                  </span>
                </td>

                <td>{g.clock || "-"}</td>
                <td>{g.period || "-"}</td>

                <td>
                  {g.winProb ? (
                    <>
                      <span className="prob home-prob">
                        {formatProb(g.winProb.home)}
                      </span>
                      {" / "}
                      <span className="prob away-prob">
                        {formatProb(g.winProb.away)}
                      </span>
                    </>
                  ) : (
                    "-"
                  )}
                </td>

                <td>
                  {g.start_time ? (
                    <span className="game-start">{g.start_time}</span>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
                );
              })()
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="live-page">
      <h1>Live Scores</h1>

      <div className="live-header-row">
        {lastUpdated && (
          <div className="updated-text">
            Updated at {formatTime(lastUpdated)}
          </div>
        )}
        <div className="refresh-hint">Auto-refreshing every 15s</div>
      </div>

      {loading && <p>Loading live games…</p>}

      {!loading && games.length === 0 && (
        <p className="no-games">No active games right now.</p>
      )}

      {games.length > 0 && (
        <>
          {renderGamesTable(liveGames, "🔴 Live Games")}
          {renderGamesTable(finishedGames, "✅ Finished Games")}
          {renderGamesTable(upcomingGames, "📅 Upcoming Games")}
        </>
      )}

      <style>{`
        .live-page {
          padding: 20px;
        }

        .games-section {
          margin-bottom: 30px;
        }

        .section-title {
          font-size: 1.3rem;
          margin-bottom: 10px;
          color: #333;
          border-bottom: 2px solid #ddd;
          padding-bottom: 5px;
        }

        .live-header-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .updated-text {
          font-size: 0.9rem;
          color: #888;
        }

        .refresh-hint {
          font-size: 0.8rem;
          color: #aaa;
        }

        .no-games {
          margin-top: 20px;
          font-size: 1.1rem;
          color: #aaa;
        }

        .live-table {
          width: 100%;
          border-collapse: collapse;
        }

        .live-table th, .live-table td {
          padding: 10px;
          border-bottom: 1px solid #ddd;
        }

        .live-table th {
          background: #333;
          color: #fff;
          font-weight: 600;
        }

        .game-row {
          cursor: pointer;
          transition: background 0.2s ease, transform 0.1s ease;
        }

        .game-row:hover {
          background: #1f2937;
          color: #f9fafb;
          transform: translateY(-1px);
        }

        .game-row:hover .home-prob {
          color: #93c5fd;
        }

        .game-row:hover .away-prob {
          color: #fca5a5;
        }

        .bet-badges {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .bet-badge {
          display: inline-flex;
          align-items: center;
          padding: 2px 8px;
          border-radius: 999px;
          font-size: 0.75rem;
          font-weight: 600;
          background: rgba(79, 70, 229, 0.2);
          color: #c7d2fe;
          border: 1px solid rgba(79, 70, 229, 0.4);
        }

        .bet-badge.home {
          background: rgba(34, 197, 94, 0.2);
          color: #bbf7d0;
          border-color: rgba(34, 197, 94, 0.4);
        }

        .bet-badge.away {
          background: rgba(248, 113, 113, 0.2);
          color: #fecaca;
          border-color: rgba(248, 113, 113, 0.4);
        }

        .bet-badge.player {
          background: rgba(14, 165, 233, 0.2);
          color: #bae6fd;
          border-color: rgba(14, 165, 233, 0.4);
        }

        .bet-badge.none {
          background: rgba(148, 163, 184, 0.2);
          color: #e2e8f0;
          border-color: rgba(148, 163, 184, 0.4);
        }

        .bet-badge.win {
          background: rgba(34, 197, 94, 0.3);
          color: #86efac;
          border-color: rgba(34, 197, 94, 0.6);
          font-weight: 700;
        }

        .bet-badge.loss {
          background: rgba(239, 68, 68, 0.3);
          color: #fca5a5;
          border-color: rgba(239, 68, 68, 0.6);
          font-weight: 700;
        }

        .status-live {
          background: rgba(0, 255, 0, 0.05);
        }

        .status-final {
          background: rgba(255, 0, 0, 0.05);
        }

        .status-scheduled {
          background: rgba(255, 255, 0, 0.05);
        }

        .score {
          transition: color 0.3s ease;
        }

        .flash {
          color: #00c853;
          font-weight: bold;
        }

        .prob {
          font-size: 0.85rem;
        }

        .home-prob {
          color: #1565c0;
        }

        .away-prob {
          color: #c62828;
        }

        .momentum {
          font-size: 0.85rem;
          color: #777;
        }

        .momentum-home {
          color: #1565c0;
          font-weight: 600;
        }

        .momentum-away {
          color: #c62828;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default LiveScoresPage;
