
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { convertToUserTimezone } from "../services/timezoneService";

function LiveScoresPage() {
  const [games, setGames] = useState([]);
  const [upcomingGames, setUpcomingGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [pendingBetsByGame, setPendingBetsByGame] = useState({});
  const [teamMomentum, setTeamMomentum] = useState({});
  const [collapsedSections, setCollapsedSections] = useState({});
  const prevScores = useRef({});
  const navigate = useNavigate();

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
      const res = await api.get("/api/live"); // already correct
      const upcomingRes = await api.get("/api/live/upcoming"); // already correct
      const betsRes = await api.get("/api/bets/all"); // now includes all bets
      const newGames = res.data || [];
      const newUpcoming = upcomingRes.data || [];
      setPendingBetsByGame(buildPendingMap(betsRes.data?.bets || []));
      // Track score changes
      newGames.forEach((g) => {
        const key = g.game_id;
        const prev = prevScores.current[key];
        g.homeScoreChanged = prev ? prev.home_score !== g.home_score : false;
        g.awayScoreChanged = prev ? prev.away_score !== g.away_score : false;
        prevScores.current[key] = {
          home_score: g.home_score,
          away_score: g.away_score,
        };
      });
      setGames(newGames);
      setUpcomingGames(newUpcoming);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to load live scores:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadMomentum = async () => {
    try {
      // Load team momentum less frequently (every 60s) as it's expensive to compute
      const momentumRes = await api.get("/api/analytics/team-momentum"); // already correct
      const momentum = momentumRes?.data || {};
      setTeamMomentum(momentum);
    } catch (err) {
      console.error("Failed to load team momentum:", err);
    }
  };

  useEffect(() => {
    loadLive();
    const liveInterval = setInterval(loadLive, 15000); // Update scores every 15s
    
    loadMomentum();
    const momentumInterval = setInterval(loadMomentum, 60000); // Update momentum every 60s
    
    // Listen for timezone changes
    const handleStorage = (e) => {
      if (e.key === "user_timezone_preference") {
        setLastUpdated(Date.now()); // force re-render
      }
    };
    window.addEventListener("storage", handleStorage);
    
    return () => {
      clearInterval(liveInterval);
      clearInterval(momentumInterval);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const formatTime = (date) => {
    if (!date) return "";
    return convertToUserTimezone(date, "time-with-tz");
  };

  const getStatusClass = (status) => {
    if (status === "ongoing") return "status-live";
    if (status === "completed") return "status-final";
    return "status-scheduled";
  };

  const getMomentumStatus = (teamId) => {
    if (!teamId || !teamMomentum[teamId]) return null;
    return teamMomentum[teamId].momentum_status;
  };

  const SPORT_ORDER = ["NFL", "NBA", "NCAAF", "NHL", "NCAAB", "SOCCER"];

  // Separate live games with active bets (sticky at top)

  // Always show all live games, regardless of pending bets
  const now = new Date();
  // Only show finished games from last 36 hours
  const finishedGames = games.filter(g => {
    if (g.status !== "completed") return false;
    const endTime = g.start_time ? new Date(g.start_time) : null;
    if (!endTime) return false;
    return (now - endTime) <= 36 * 60 * 60 * 1000; // 36 hours in ms
  });

  // Only show upcoming games within next 24 hours
  const sortedUpcomingGames = (upcomingGames || [])
    .filter(g => {
      const status = String(g.status || '').toLowerCase();
      const startTime = g.start_time ? new Date(g.start_time) : null;
      if (!startTime) return false;
      // Accept if scheduled and within next 24 hours
      return (
        (status === 'scheduled' || (!status && startTime > now) || (status !== 'ongoing' && status !== 'completed' && startTime > now)) &&
        (startTime - now) <= 24 * 60 * 60 * 1000 && (startTime - now) >= 0
      );
    })
    .sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time) : new Date(0);
      const bTime = b.start_time ? new Date(b.start_time) : new Date(0);
      return aTime - bTime;
    });

  // For sticky section, show games with any attached bets (pending, won, lost)
  const liveGamesWithBets = games.filter(g => {
    if (g.status !== "ongoing") return false;
    const betInfo = pendingBetsByGame[g.game_id];
    // Show if any bets (pending, won, lost) are attached
    return betInfo && (
      betInfo.selections.length > 0 ||
      betInfo.players.length > 0 ||
      betInfo.finished.length > 0
    );
  });
  const liveGamesWithoutBets = games.filter(g =>
    g.status === "ongoing" && !liveGamesWithBets.some(betGame => betGame.game_id === g.game_id)
  );

  const groupGamesBySport = (gamesList) => {
    const grouped = {};
    gamesList.forEach(g => {
      const sport = (g.sport || "OTHER").toUpperCase();
      if (!grouped[sport]) {
        grouped[sport] = [];
      }
      grouped[sport].push(g);
    });

    const sorted = {};
    SPORT_ORDER.forEach(sport => {
      if (grouped[sport]) {
        sorted[sport] = grouped[sport];
      }
    });
    Object.keys(grouped).forEach(sport => {
      if (!sorted[sport]) {
        sorted[sport] = grouped[sport];
      }
    });
    return sorted;
  };

  // Removed broken/duplicate renderSportTable and loadLive
  // Render a table for a list of games
  const renderGamesTable = (gamesList, title) => {
    if (!gamesList || gamesList.length === 0) return null;
    return (
      <div className="games-section">
        <h2 className="section-title">{title}</h2>
        <div>
          {groupGamesBySport(gamesList) &&
            Object.entries(groupGamesBySport(gamesList)).map(([sport, sportGames]) => (
              <div className="sport-table-container" key={sport}>
                <h3 className="sport-subtitle">{sport}</h3>
                <table className="table live-table">
                  <thead>
                    <tr>
                      <th>Matchup</th>
                      <th>Bets</th>
                      {title === "✅ Finished Games" && <th>Score</th>}
                      {title !== "✅ Finished Games" && title !== "📅 Upcoming Games" && <th>Score</th>}
                      {title !== "✅ Finished Games" && title !== "📅 Upcoming Games" && <th>Clock</th>}
                      {title !== "✅ Finished Games" && title !== "📅 Upcoming Games" && <th>Period</th>}
                      {title === "📅 Upcoming Games" && <th>Start Time</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {sportGames.map((g) => {
                      const pendingInfo = pendingBetsByGame[g.game_id];
                      const selections = pendingInfo?.selections || [];
                      const players = pendingInfo?.players || [];
                      const finished = pendingInfo?.finished || [];
                      const hasHomeBet = teamMatchesSelection(g.home_team, selections);
                      const hasAwayBet = teamMatchesSelection(g.away_team, selections);
                      const hasPlayerBet = players.length > 0;
                      const homeMomentum = getMomentumStatus(g.home_team_id);
                      const awayMomentum = getMomentumStatus(g.away_team_id);
                      // Bets column content
                      let betsContent = null;
                      if (hasHomeBet || hasAwayBet || hasPlayerBet || finished.length > 0) {
                        betsContent = (
                          <div className="bet-badges">
                            {hasHomeBet && <span className="bet-badge home">Home</span>}
                            {hasAwayBet && <span className="bet-badge away">Away</span>}
                            {hasPlayerBet && (
                              <span className="bet-badge player" title={players.join(", ")}>Player ({players.length})</span>
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
                        );
                      } else {
                        betsContent = <span className="bet-badge none">None</span>;
                      }
                      return (
                        <tr
                          key={g.game_id}
                          className={`game-row ${getStatusClass(g.status)}`}
                          onClick={() => navigate(`/games/${g.game_id}/details`)}
                        >
                          <td>
                            <div className="matchup-container">
                              <span className="team-name">
                                {g.home_logo && <img src={g.home_logo} className="team-logo" alt="" />}
                                {g.home_team}
                                {homeMomentum === "FIRE" && <span className="momentum-badge fire">🔥 FIRE</span>}
                                {homeMomentum === "FREEZING" && <span className="momentum-badge freezing">🧊 FREEZING</span>}
                              </span>
                              <span className="vs-text"> vs </span>
                              <span className="team-name">
                                {g.away_logo && <img src={g.away_logo} className="team-logo" alt="" />}
                                {g.away_team}
                                {awayMomentum === "FIRE" && <span className="momentum-badge fire">🔥 FIRE</span>}
                                {awayMomentum === "FREEZING" && <span className="momentum-badge freezing">🧊 FREEZING</span>}
                              </span>
                            </div>
                          </td>
                          <td>{betsContent}</td>
                          {title === "✅ Finished Games" && (
                            <td>
                              <span className={g.homeScoreChanged ? "score flash" : "score"}>{g.home_score}</span>
                              {" - "}
                              <span className={g.awayScoreChanged ? "score flash" : "score"}>{g.away_score}</span>
                            </td>
                          )}
                          {title !== "✅ Finished Games" && title !== "📅 Upcoming Games" && (
                            <td>
                              <span className={g.homeScoreChanged ? "score flash" : "score"}>{g.home_score}</span>
                              {" - "}
                              <span className={g.awayScoreChanged ? "score flash" : "score"}>{g.away_score}</span>
                            </td>
                          )}
                          {title !== "✅ Finished Games" && title !== "📅 Upcoming Games" && (
                            <>
                              <td>{g.clock || "-"}</td>
                              <td>{g.period || "-"}</td>
                            </>
                          )}
                          {title === "📅 Upcoming Games" && (
                            <td>
                              {g.start_time ? (
                                <div className="game-time-stack">
                                  <span className="game-date">{convertToUserTimezone(g.start_time, "date")}</span>
                                  <span className="game-time">{convertToUserTimezone(g.start_time, "time-with-tz")}</span>
                                </div>
                              ) : (
                                "-"
                              )}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ))}
        </div>
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
        <div className="refresh-hint">Auto-refreshing every 2 minutes</div>
      </div>

      {loading && <p>Loading live games…</p>}


      {/* Always render in this order: Live games with bets, other live games, upcoming games, finished games */}
      {!loading && liveGamesWithBets.length > 0 && (
        <div className="sticky-games-section">
          <h2 className="sticky-games-title">
            📌 Live Games with Active Bets
          </h2>
          <div className="sticky-games-container">
            {liveGamesWithBets.map((g) => (
              (() => {
                const pendingInfo = pendingBetsByGame[g.game_id];
                const selections = pendingInfo?.selections || [];
                const players = pendingInfo?.players || [];
                const finished = pendingInfo?.finished || [];
                const hasHomeBet = teamMatchesSelection(g.home_team, selections);
                const hasAwayBet = teamMatchesSelection(g.away_team, selections);
                const hasPlayerBet = players.length > 0;
                const homeMomentum = getMomentumStatus(g.home_team_id);
                const awayMomentum = getMomentumStatus(g.away_team_id);
                return (
                  <table key={g.game_id} className="table live-table sticky-game-table">
                    <tbody>
                      <tr
                        className={`game-row ${getStatusClass(g.status)}`}
                        onClick={() => navigate(`/games/${g.game_id}/details`)}>
                        <td>
                          <div className="matchup-container">
                            <span className="team-name">
                              {g.home_logo && <img src={g.home_logo} className="team-logo" alt="" />}
                              {g.home_team}
                              {homeMomentum === "FIRE" && <span className="momentum-badge fire">🔥 FIRE</span>}
                              {homeMomentum === "FREEZING" && <span className="momentum-badge freezing">🧊 FREEZING</span>}
                            </span>
                            <span className="vs-text"> vs </span>
                            <span className="team-name">
                              {g.away_logo && <img src={g.away_logo} className="team-logo" alt="" />}
                              {g.away_team}
                              {awayMomentum === "FIRE" && <span className="momentum-badge fire">🔥 FIRE</span>}
                              {awayMomentum === "FREEZING" && <span className="momentum-badge freezing">🧊 FREEZING</span>}
                            </span>
                          </div>
                        </td>
                        <td>
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
                        </td>
                        <td>
                          <span className={g.homeScoreChanged ? "score flash" : "score"}>
                            {g.home_score}
                          </span>
                          {" - "}
                          <span className={g.awayScoreChanged ? "score flash" : "score"}>
                            {g.away_score}
                          </span>
                        </td>
                        <td>{g.clock || "-"}</td>
                        <td>{g.period || "-"}</td>
                      </tr>
                    </tbody>
                  </table>
                );
              })()
            ))}
          </div>
        </div>
      )}

      {!loading && liveGamesWithoutBets.length > 0 && (
        <>
          {renderGamesTable(liveGamesWithoutBets, "🔴 Live Games")}
        </>
      )}

      {!loading && sortedUpcomingGames.length > 0 && (
        <>
          {renderGamesTable(sortedUpcomingGames, "📅 Upcoming Games")}
        </>
      )}

      {!loading && finishedGames.length > 0 && (
        <>
          {renderGamesTable(finishedGames, "✅ Finished Games")}
        </>
      )}
      {/* ...existing code... */}
      <style>{`
        .live-page {
          padding: 32px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        }
        .live-page h1 {
          font-size: 2.2rem;
          font-weight: 700;
          margin: 0 0 24px 0;
          background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .sticky-games-section {
          margin-bottom: 32px;
          padding: 20px;
          background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%);
          border: 2px solid rgba(239, 68, 68, 0.3);
          border-radius: 16px;
          box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
        }
        .sticky-games-title {
          font-size: 1.3rem;
          font-weight: 800;
          margin: 0 0 16px 0;
          color: #ef4444;
          text-transform: uppercase;
          letter-spacing: 1px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .sticky-games-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .sticky-game-table {
          margin: 0 !important;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }
        .sticky-game-table .game-row {
          background: transparent !important;
          color: #ffffff !important;
        }
        .sticky-game-table .game-row td {
          color: #ffffff !important;
        }
        .sticky-game-table .team-name {
          color: #ffffff !important;
        }
        .sticky-game-table .vs-text {
          color: rgba(255, 255, 255, 0.7) !important;
        }
        .sticky-game-table .score {
          color: #ffffff !important;
          font-weight: 600;
        }
        .sticky-game-table .game-row:hover {
          background: rgba(239, 68, 68, 0.12) !important;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
        }
        /* Dark mode styles for sticky games table */
        @media (prefers-color-scheme: dark) {
          .sticky-games-section {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.15) 100%);
            border: 2px solid rgba(239, 68, 68, 0.4);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
          }
          .sticky-games-title {
            color: #f87171; /* Brighter red for dark mode */
          }
          .sticky-game-table {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
          }
          .sticky-game-table .game-row {
            background: transparent !important;
          }
          .sticky-game-table .game-row:hover {
            background: rgba(239, 68, 68, 0.18) !important;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
          }
        }
        .games-section {
          margin-bottom: 40px;
        }
        .sport-table-container {
          margin-bottom: 24px;
          border-radius: 12px;
          overflow: hidden;
          border: 1px solid rgba(15, 118, 110, 0.15);
          background: rgba(15, 118, 110, 0.02);
          backdrop-filter: blur(10px);
        }
        .sport-subtitle {
          font-size: 1.1rem;
          margin: 0;
          color: #fff;
          font-weight: 900;
          padding: 12px 16px;
          background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
          border-bottom: 1px solid rgba(15, 118, 110, 0.3);
          text-transform: uppercase;
          letter-spacing: 1px;
          line-height: 1.2;
          display: block;
        }
        .sport-table-container table {
          margin-top: 0;
        }
        .section-title {
          font-size: 1.5rem;
          margin: 0 0 20px 0;
          color: #0d9488;
          font-weight: 700;
          cursor: pointer;
          user-select: none;
          display: flex;
          align-items: center;
          gap: 12px;
          transition: all 0.3s ease;
          padding: 12px 0 12px 0;
          border-bottom: 2px solid rgba(13, 148, 136, 0.4);
          position: sticky;
          top: 0;
          z-index: 40;
          background: #1a1a1a;
        }
        .section-title:hover {
          color: #0f766e;
          border-bottom: 2px solid #0d9488;
        }
        .collapse-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          font-size: 0.9rem;
          transition: transform 0.3s ease;
          color: #0d9488;
        }
        .section-title:hover .collapse-icon {
          transform: scale(1.1);
        }
        .live-header-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding: 16px;
          background: rgba(15, 118, 110, 0.05);
          border-radius: 8px;
          border-left: 4px solid #0d9488;
        }
        .updated-text {
          font-size: 0.85rem;
          color: #0f766e;
          font-weight: 500;
          font-variant-numeric: tabular-nums;
        }
        .refresh-hint {
          font-size: 0.8rem;
          color: #0d9488;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .refresh-hint::before {
          content: '⟳';
          display: inline-block;
          animation: spin 2s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .no-games {
          margin-top: 40px;
          font-size: 1.1rem;
          color: #999;
          text-align: center;
          padding: 40px;
          background: rgba(0, 0, 0, 0.02);
          border-radius: 8px;
          border: 2px dashed rgba(0, 0, 0, 0.1);
        }
        .live-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.95rem;
          margin: 0;
        }
        .live-table th {
          background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
          color: #fff;
          font-weight: 700;
          text-align: left;
          padding: 14px 16px;
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border: none;
        }
        .live-table td {
          padding: 14px 16px;
          border-bottom: 1px solid rgba(15, 118, 110, 0.08);
          color: #f0f0f0;
          white-space: nowrap;
        }
        .game-row {
          cursor: pointer;
          transition: all 0.2s ease;
          border-bottom: 1px solid rgba(15, 118, 110, 0.08);
        }
        .game-row:hover {
          background: linear-gradient(90deg, rgba(15, 118, 110, 0.08), rgba(13, 148, 136, 0.04));
          transform: translateX(4px);
          border-left: 3px solid #0d9488;
          padding-left: 13px;
        }
        .bet-badges {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .bet-badge {
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.72rem;
          font-weight: 700;
          background: rgba(79, 70, 229, 0.15);
          color: #fff !important;
          border: 1px solid rgba(79, 70, 229, 0.3);
          text-transform: uppercase;
          letter-spacing: 0.3px;
          transition: all 0.2s ease;
        }
        .bet-badge:hover {
          transform: scale(1.05);
          box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2);
        }
        .bet-badge.home {
          background: rgba(34, 197, 94, 0.15);
          color: #fff !important;
          border-color: rgba(34, 197, 94, 0.4);
        }
        .bet-badge.away {
          background: rgba(248, 113, 113, 0.15);
          color: #fff !important;
          border-color: rgba(248, 113, 113, 0.4);
        }
        .bet-badge.player {
          background: rgba(14, 165, 233, 0.15);
          color: #fff !important;
          border-color: rgba(14, 165, 233, 0.4);
        }
        .bet-badge.none {
          background: rgba(148, 163, 184, 0.1);
          color: #fff !important;
          border-color: rgba(148, 163, 184, 0.3);
          opacity: 0.7;
        }
        .bet-badge.win {
          background: rgba(34, 197, 94, 0.25);
          color: #fff !important;
          border-color: rgba(34, 197, 94, 0.6);
          font-weight: 800;
          box-shadow: 0 0 8px rgba(34, 197, 94, 0.3);
        }
        .bet-badge.loss {
          background: rgba(239, 68, 68, 0.25);
          color: #fff !important;
          border-color: rgba(239, 68, 68, 0.6);
          font-weight: 800;
          box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
        }
        .status-live {
          background: linear-gradient(90deg, rgba(34, 197, 94, 0.08), transparent);
          border-left: 3px solid #22c55e;
        }
        .status-final {
          background: linear-gradient(90deg, rgba(239, 68, 68, 0.08), transparent);
          border-left: 3px solid #ef4444;
        }
        .status-scheduled {
          background: linear-gradient(90deg, rgba(245, 158, 11, 0.08), transparent);
          border-left: 3px solid #f59e0b;
        }
        .score {
          font-weight: 700;
          font-size: 1.05rem;
          transition: all 0.2s ease;
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }
        .flash {
          color: #22c55e;
          font-weight: 900;
          animation: glow 0.6s ease-out;
        }
        @keyframes glow {
          0% {
            text-shadow: 0 0 10px #22c55e;
            transform: scale(1.1);
          }
          100% {
            text-shadow: none;
            transform: scale(1);
          }
        }
        .game-date {
          font-weight: 700;
          color: #0d9488;
          font-size: 0.9rem;
        }
        .game-time-stack {
          display: flex;
          flex-direction: column;
          gap: 4px;
          align-items: flex-start;
        }
        .game-time-stack .game-date {
          font-size: 0.9rem;
          font-weight: 700;
          color: #0f766e;
        }
        .game-time-stack .game-time {
          font-size: 0.8rem;
          color: #999;
          font-variant-numeric: tabular-nums;
        }
        .matchup-container {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .team-name {
          display: flex;
          align-items: center;
          gap: 10px;
          font-weight: 700;
          color: #f0f0f0;
        }
        .team-logo {
          width: 36px;
          height: 36px;
          object-fit: contain;
          border-radius: 6px;
          background: linear-gradient(135deg, rgba(15, 118, 110, 0.1), rgba(13, 148, 136, 0.1));
          padding: 3px;
          transition: transform 0.2s ease;
        }
        .team-name:hover .team-logo {
          transform: scale(1.08) rotate(2deg);
        }
        .vs-text {
          color: #666;
          font-size: 0.75rem;
          margin: 0;
          font-weight: 400;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }
        .momentum-badge {
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.65rem;
          font-weight: 800;
          white-space: nowrap;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-left: 6px;
        }
        .momentum-badge.fire {
          background: linear-gradient(135deg, rgba(255, 87, 34, 0.25), rgba(244, 67, 54, 0.25));
          color: #ea580c;
          border: 1.5px solid rgba(255, 87, 34, 0.6);
          animation: pulse-fire 2s infinite;
          box-shadow: 0 0 8px rgba(255, 87, 34, 0.3);
        }
        .momentum-badge.freezing {
          background: linear-gradient(135deg, rgba(33, 150, 243, 0.25), rgba(3, 169, 244, 0.25));
          color: #0284c7;
          border: 1.5px solid rgba(33, 150, 243, 0.6);
          animation: pulse-freeze 2s infinite;
          box-shadow: 0 0 8px rgba(33, 150, 243, 0.3);
        }
        @keyframes pulse-fire {
          0%, 100% {
            box-shadow: 0 0 8px rgba(255, 87, 34, 0.3);
            transform: scale(1);
          }
          50% {
            box-shadow: 0 0 16px rgba(255, 87, 34, 0.6);
            transform: scale(1.02);
          }
        }
        @keyframes pulse-freeze {
          0%, 100% {
            box-shadow: 0 0 8px rgba(33, 150, 243, 0.3);
            transform: scale(1);
          }
          50% {
            box-shadow: 0 0 16px rgba(33, 150, 243, 0.6);
            transform: scale(1.02);
          }
        }
        .live-table tr {
          transition: all 0.2s ease;
        }
        .live-table tbody tr:last-child td {
          border-bottom: none;
        }
      `}</style>
    </div>
  );
}

export default LiveScoresPage;
