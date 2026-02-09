import React, { useState, useEffect } from "react";
import api from "../services/api.js";

function PropExplorerPage() {
  const [players, setPlayers] = useState([]);
  const [filteredPlayers, setFilteredPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [sportFilter, setSportFilter] = useState("all");
  const [teamFilter, setTeamFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  
  // Stats display
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [playerStats, setPlayerStats] = useState([]);
  const [loadingStats, setLoadingStats] = useState(false);

  // Load all players on mount
  useEffect(() => {
    loadPlayers();
  }, []);

  // Apply filters whenever they change
  useEffect(() => {
    applyFilters();
  }, [sportFilter, teamFilter, searchQuery, players]);

  const loadPlayers = async () => {
    try {
      setLoading(true);
      const res = await api.get("/props/players");
      setPlayers(res.data || []);
    } catch (err) {
      console.error("Failed to load players:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadPlayerStats = async (playerId) => {
    try {
      setLoadingStats(true);
      const res = await api.get(`/props/players/${playerId}/stats`);
      setPlayerStats(res.data || []);
    } catch (err) {
      console.error("Failed to load player stats:", err);
      setPlayerStats([]);
    } finally {
      setLoadingStats(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...players];

    // Sport filter
    if (sportFilter !== "all") {
      filtered = filtered.filter(p => p.sport === sportFilter);
    }

    // Team filter
    if (teamFilter !== "all") {
      filtered = filtered.filter(p => p.team_id === teamFilter);
    }

    // Search query (name)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(p => 
        (p.full_name || "").toLowerCase().includes(query) ||
        (p.name || "").toLowerCase().includes(query)
      );
    }

    setFilteredPlayers(filtered);
  };

  const handlePlayerSelect = (player) => {
    setSelectedPlayer(player);
    loadPlayerStats(player.player_id);
  };

  const getUniqueSports = () => {
    const sports = [...new Set(players.map(p => p.sport).filter(Boolean))];
    return sports.sort();
  };

  const getUniqueTeams = () => {
    let teamPlayers = players;
    if (sportFilter !== "all") {
      teamPlayers = players.filter(p => p.sport === sportFilter);
    }
    // Create array of unique teams with both id and name
    const teamMap = new Map();
    teamPlayers.forEach(p => {
      if (p.team_id && !teamMap.has(p.team_id)) {
        teamMap.set(p.team_id, p.team_name || p.team_id);
      }
    });
    // Return sorted array of objects
    return Array.from(teamMap.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  };

  const calculateAverage = (statName) => {
    if (playerStats.length === 0) return "-";
    const values = playerStats
      .map(s => s[statName])
      .filter(v => v != null && !isNaN(v));
    if (values.length === 0) return "-";
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    return avg.toFixed(1);
  };

  const getRelevantStats = () => {
    if (!selectedPlayer) return [];
    
    const sport = selectedPlayer.sport;
    if (sport === "NBA" || sport === "NCAAB") {
      return [
        { label: "Points", key: "points" },
        { label: "Rebounds", key: "rebounds" },
        { label: "Assists", key: "assists" },
        { label: "Steals", key: "steals" },
        { label: "Blocks", key: "blocks" },
        { label: "3PT Made", key: "three_pt" },
      ];
    } else if (sport === "NFL" || sport === "NCAAF") {
      return [
        { label: "Passing Yards", key: "passing_yards" },
        { label: "Passing TDs", key: "passing_tds" },
        { label: "Rushing Yards", key: "rushing_yards" },
        { label: "Rushing TDs", key: "rushing_tds" },
        { label: "Receiving Yards", key: "receiving_yards" },
        { label: "Receiving TDs", key: "receiving_tds" },
        { label: "Interceptions", key: "interceptions" },
      ];
    } else if (sport === "NHL") {
      return [
        { label: "Goals", key: "nhl_goals" },
        { label: "Assists", key: "nhl_assists" },
        { label: "Points", key: "points" },
        { label: "Shots on Goal", key: "nhl_shots" },
        { label: "Hits", key: "nhl_hits" },
        { label: "+/-", key: "nhl_plus_minus" },
      ];
    } else if (sport === "MLB") {
      return [
        { label: "Hits", key: "hits" },
        { label: "Runs", key: "runs" },
        { label: "RBI", key: "rbi" },
        { label: "Home Runs", key: "hr" },
        { label: "Stolen Bases", key: "sb" },
        { label: "Strikeouts", key: "so" },
      ];
    }
    return [];
  };

  return (
    <div className="prop-explorer-page">
      <h1>Prop Explorer</h1>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Sport:</label>
          <select value={sportFilter} onChange={(e) => setSportFilter(e.target.value)}>
            <option value="all">All Sports</option>
            {getUniqueSports().map(sport => (
              <option key={sport} value={sport}>{sport}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Team:</label>
          <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
            <option value="all">All Teams</option>
            {getUniqueTeams().map(team => (
              <option key={team.id} value={team.id}>{team.name}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Search Player:</label>
          <input
            type="text"
            placeholder="Enter player name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-actions">
          <button onClick={() => {
            setSportFilter("all");
            setTeamFilter("all");
            setSearchQuery("");
          }}>Clear Filters</button>
        </div>
      </div>

      <div className="results-summary">
        {loading ? "Loading..." : `${filteredPlayers.length} players found`}
      </div>

      <div className="prop-content">
        <div className="players-list">
          <h3>Players</h3>
          {filteredPlayers.length === 0 && !loading && (
            <p className="no-results">No players match your filters</p>
          )}
          <div className="player-cards">
            {filteredPlayers.map(player => (
              <div
                key={player.player_id}
                className={`player-card ${selectedPlayer?.player_id === player.player_id ? "selected" : ""}`}
                onClick={() => handlePlayerSelect(player)}
              >
                {player.headshot && (
                  <img src={player.headshot} alt={player.full_name} className="player-headshot" />
                )}
                <div className="player-info">
                  <div className="player-name">{player.full_name || player.name}</div>
                  <div className="player-meta">
                    {player.position && <span className="position">{player.position}</span>}
                    {player.team_name && <span className="team">{player.team_name}</span>}
                  </div>
                  <div className="player-sport">{player.sport}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="stats-panel">
          {!selectedPlayer && (
            <div className="no-selection">
              <p>← Select a player to view statistics</p>
            </div>
          )}

          {selectedPlayer && (
            <>
              <div className="player-header">
                {selectedPlayer.headshot && (
                  <img src={selectedPlayer.headshot} alt={selectedPlayer.full_name} className="player-headshot-large" />
                )}
                <div>
                  <h2>{selectedPlayer.full_name || selectedPlayer.name}</h2>
                  <div className="player-details">
                    <span>{selectedPlayer.position}</span> • 
                    <span>{selectedPlayer.team_id}</span> • 
                    <span>{selectedPlayer.sport}</span>
                  </div>
                </div>
              </div>

              {loadingStats && <p>Loading stats...</p>}

              {!loadingStats && playerStats.length === 0 && (
                <p className="no-stats">No statistics available for this player</p>
              )}

              {!loadingStats && playerStats.length > 0 && (
                <>
                  <div className="stats-summary">
                    <h3>Season Averages ({playerStats.length} games)</h3>
                    <div className="stat-cards">
                      {getRelevantStats().map(stat => (
                        <div key={stat.key} className="stat-card">
                          <div className="stat-label">{stat.label}</div>
                          <div className="stat-value">{calculateAverage(stat.key)}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="recent-games">
                    <h3>Recent Games</h3>
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>Game</th>
                          {getRelevantStats().map(stat => (
                            <th key={stat.key}>{stat.label}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {playerStats.slice(0, 10).map((stat, idx) => (
                          <tr key={idx}>
                            <td>{stat.game_id}</td>
                            {getRelevantStats().map(s => (
                              <td key={s.key}>{stat[s.key] ?? "-"}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>

      <style>{`
        .prop-explorer-page {
          padding: 20px;
          color: white;
        }

        .prop-explorer-page h1 {
          color: white;
          font-size: 2.5rem;
          font-weight: 700;
          margin-bottom: 30px;
        }

        .filters-bar {
          display: flex;
          gap: 15px;
          margin-bottom: 20px;
          padding: 15px;
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          flex-wrap: wrap;
        }

        .filter-group {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }

        .filter-group label {
          font-size: 0.85rem;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.9);
        }

        .filter-group select,
        .filter-group input {
          padding: 8px 12px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 4px;
          font-size: 0.9rem;
          background: rgba(0, 0, 0, 0.3);
          color: white;
        }

        .filter-group select option {
          background: #2a2a3e;
          color: white;
        }

        .filter-group input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .filter-actions {
          display: flex;
          align-items: flex-end;
        }

        .filter-actions button {
          padding: 8px 16px;
          background: #f44336;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: background 0.2s;
        }

        .filter-actions button:hover {
          background: #d32f2f;
        }

        .results-summary {
          margin-bottom: 15px;
          font-size: 0.95rem;
          color: rgba(255, 255, 255, 0.7);
        }

        .prop-content {
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 20px;
        }

        .players-list {
          border-right: 1px solid rgba(255, 255, 255, 0.1);
          padding-right: 20px;
        }

        .players-list h3 {
          margin-top: 0;
          margin-bottom: 15px;
          color: white;
        }

        .player-cards {
          display: flex;
          flex-direction: column;
          gap: 10px;
          max-height: 600px;
          overflow-y: auto;
        }

        .player-card {
          display: flex;
          gap: 10px;
          padding: 10px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
          background: rgba(0, 0, 0, 0.2);
        }

        .player-card:hover {
          background: rgba(255, 255, 255, 0.08);
          transform: translateX(4px);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .player-card.selected {
          background: rgba(74, 144, 226, 0.2);
          border-color: #4a90e2;
        }

        .player-headshot {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          object-fit: cover;
        }

        .player-info {
          flex: 1;
        }

        .player-name {
          font-weight: 600;
          margin-bottom: 4px;
          color: white;
        }

        .player-meta {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
          display: flex;
          gap: 8px;
        }

        .player-sport {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.5);
          margin-top: 2px;
        }

        .position {
          background: rgba(76, 175, 80, 0.8);
          color: white;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 0.75rem;
        }

        .stats-panel {
          padding-left: 20px;
        }

        .no-selection {
          text-align: center;
          color: rgba(255, 255, 255, 0.5);
          padding: 40px 20px;
        }

        .player-header {
          display: flex;
          gap: 15px;
          align-items: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        .player-headshot-large {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          object-fit: cover;
        }

        .player-header h2 {
          margin: 0 0 8px 0;
          color: white;
        }

        .player-details {
          color: rgba(255, 255, 255, 0.7);
          font-size: 0.95rem;
        }

        .player-details span {
          margin: 0 8px;
        }

        .stats-summary {
          margin-bottom: 30px;
        }

        .stats-summary h3 {
          margin-bottom: 15px;
          color: white;
        }

        .stat-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 15px;
        }

        .stat-card {
          background: linear-gradient(135deg, #2a2a3e 0%, #3a3a4e 100%);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 15px;
          border-radius: 6px;
          text-align: center;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        }

        .stat-label {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 8px;
        }

        .stat-value {
          font-size: 1.8rem;
          font-weight: 700;
          color: #4a90e2;
        }

        .recent-games h3 {
          margin-bottom: 15px;
          color: white;
        }

        .stats-table {
          width: 100%;
          border-collapse: collapse;
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          overflow: hidden;
        }

        .stats-table th,
        .stats-table td {
          padding: 10px;
          text-align: left;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stats-table th {
          background: rgba(0, 0, 0, 0.4);
          color: white;
          font-weight: 600;
          font-size: 0.9rem;
        }

        .stats-table td {
          font-size: 0.9rem;
          color: rgba(255, 255, 255, 0.9);
        }

        .stats-table tr:hover {
          background: rgba(255, 255, 255, 0.08);
        }

        .stats-table tbody tr:last-child td {
          border-bottom: none;
        }

        .no-results,
        .no-stats {
          text-align: center;
          color: rgba(255, 255, 255, 0.5);
          padding: 20px;
        }
      `}</style>
    </div>
  );
}

export default PropExplorerPage;