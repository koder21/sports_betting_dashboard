import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api.js";

function GameIntelPage() {
  const { gameId } = useParams();
  const [intel, setIntel] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("team");

  useEffect(() => {
    if (!gameId) return;
    let active = true;
    setLoading(true);
    api
      .get(`/games/${gameId}`)
      .then((res) => {
        if (active) setIntel(res.data || null);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [gameId]);

  const teamStats = useMemo(() => extractTeamStats(intel?.boxscore, intel), [intel]);
  const playerColumns = useMemo(
    () => getPlayerColumns(intel?.home_stats || [], intel?.away_stats || []),
    [intel]
  );

  if (loading) return <div>Loading...</div>;
  if (!intel) return <div>No data.</div>;

  const scoreInfo = getScoreInfo(intel);

  return (
    <div className="game-intel-page">
      <div className="game-header">
        <div>
          <h1>Game Details</h1>
          <p className="subtitle">Game #{intel.game_id}</p>
        </div>
        <div className="score-card">
          <div className="team-line">
            <span className="team-name">{scoreInfo.homeTeam}</span>
            <span className="team-score">{scoreInfo.homeScore ?? "-"}</span>
          </div>
          <div className="team-line">
            <span className="team-name">{scoreInfo.awayTeam}</span>
            <span className="team-score">{scoreInfo.awayScore ?? "-"}</span>
          </div>
          <div className="status-line">
            <span>{scoreInfo.status || "-"}</span>
            {scoreInfo.clock && <span> • {scoreInfo.clock}</span>}
            {scoreInfo.period && <span> • {scoreInfo.period}</span>}
          </div>
        </div>
      </div>

      <div className="tabs">
        <button
          className={activeTab === "team" ? "tab active" : "tab"}
          onClick={() => setActiveTab("team")}
        >
          Team Stats
        </button>
        <button
          className={activeTab === "players" ? "tab active" : "tab"}
          onClick={() => setActiveTab("players")}
        >
          Player Stats
        </button>
      </div>
      {activeTab === "team" && (
        <div className="team-stats">
          {teamStats.stats.length === 0 ? (
            <div className="empty">No team stats available for this game.</div>
          ) : (
            <table className="stats-table">
              <thead>
                <tr>
                  <th>Stat</th>
                  <th>{teamStats.homeName}</th>
                  <th>{teamStats.awayName}</th>
                </tr>
              </thead>
              <tbody>
                {teamStats.stats.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    <td>{row.home ?? "-"}</td>
                    <td>{row.away ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === "players" && (
        <div className="player-stats">
          <h3>{intel.home_team}</h3>
          {renderPlayerTable(intel.home_stats, playerColumns)}

          <h3>{intel.away_team}</h3>
          {renderPlayerTable(intel.away_stats, playerColumns)}
        </div>
      )}

      <style>{`
        .game-intel-page {
          padding: 20px;
        }
        .game-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .subtitle {
          color: #666;
          margin-top: 4px;
        }
        .score-card {
          background: #0f172a;
          color: #fff;
          padding: 12px 16px;
          border-radius: 10px;
          min-width: 260px;
        }
        .team-line {
          display: flex;
          justify-content: space-between;
          font-weight: 600;
          margin-bottom: 6px;
        }
        .team-score {
          font-size: 1.1rem;
        }
        .status-line {
          font-size: 0.9rem;
          color: #cbd5e1;
        }
        .tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }
        .tab {
          border: 1px solid #ddd;
          background: #fff;
          padding: 8px 12px;
          border-radius: 8px;
          cursor: pointer;
        }
        .tab.active {
          background: #2563eb;
          color: #fff;
          border-color: #2563eb;
        }
        .stats-table {
          width: 100%;
          border-collapse: collapse;
        }
        .stats-table th,
        .stats-table td {
          padding: 10px;
          border-bottom: 1px solid #eee;
          text-align: left;
        }
        .stats-table th {
          background: #111827;
          color: #fff;
          font-size: 0.9rem;
        }
        .empty {
          color: #888;
          padding: 12px 0;
        }
        .player-stats h3 {
          margin-top: 16px;
        }
      `}</style>
    </div>
  );
}

function getScoreInfo(intel) {
  const live = intel?.live || {};
  const result = intel?.result || {};
  const game = intel?.game || {};

  return {
    homeTeam:
      live.home_team_name ||
      result.home_team_name ||
      intel.home_team ||
      game.home_team_name ||
      "Home",
    awayTeam:
      live.away_team_name ||
      result.away_team_name ||
      intel.away_team ||
      game.away_team_name ||
      "Away",
    homeScore: live.home_score ?? result.home_score ?? game.home_score,
    awayScore: live.away_score ?? result.away_score ?? game.away_score,
    status: intel.status || live.status || result.status || game.status,
    clock: live.clock || game.clock,
    period: live.period || game.period,
  };
}

function extractTeamStats(boxscore, intel) {
  const teams = boxscore?.teams || [];
  const homeName = teams[0]?.team?.displayName || intel?.home_team || "Home";
  const awayName = teams[1]?.team?.displayName || intel?.away_team || "Away";

  const homeStats = normalizeTeamStats(teams[0]);
  const awayStats = normalizeTeamStats(teams[1]);

  const labels = Array.from(new Set([...Object.keys(homeStats), ...Object.keys(awayStats)]));
  const stats = labels.map((label) => ({
    label,
    home: homeStats[label],
    away: awayStats[label],
  }));

  return { homeName, awayName, stats };
}

function normalizeTeamStats(team) {
  const stats = {};
  const list = team?.statistics || team?.stats || [];
  list.forEach((s) => {
    const label = s.label || s.name || s.displayName;
    const value = s.displayValue ?? s.value ?? s.display;
    if (label) stats[label] = value;
  });
  return stats;
}

function getPlayerColumns(homeStats, awayStats) {
  const exclude = new Set([
    "id",
    "game_id",
    "player_id",
    "team_id",
    "sport",
    "league",
    "created_at",
    "updated_at",
    "stats_json",
  ]);

  const collect = (list) =>
    list.flatMap((p) => Object.keys(p?.stats || {})).filter((k) => !exclude.has(k));

  const keys = Array.from(new Set([...collect(homeStats), ...collect(awayStats)]));
  return keys.slice(0, 10);
}

function renderPlayerTable(rows, columns) {
  if (!rows || rows.length === 0) {
    return <div className="empty">No player stats available.</div>;
  }

  return (
    <table className="stats-table">
      <thead>
        <tr>
          <th>Player</th>
          {columns.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.player}>
            <td>{row.player}</td>
            {columns.map((c) => (
              <td key={c}>{row.stats?.[c] ?? "-"}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default GameIntelPage;