import React, { useEffect, useState } from "react";
import api from "../services/api.js";
import "./SportsAnalyticsPage.css";

function SportsAnalyticsPage() {
  const [activeSport, setActiveSport] = useState("NBA");
  const [sportData, setSportData] = useState(null);
  const [loading, setLoading] = useState(true);

  const sports = [
    { code: "NBA", name: "NBA", icon: "🏀" },
    { code: "NCAAB", name: "NCAAB", icon: "🎓" },
    { code: "NFL", name: "NFL", icon: "🏈" },
    { code: "NHL", name: "NHL", icon: "🏒" },
    { code: "EPL", name: "EPL", icon: "⚽" },
  ];

  useEffect(() => {
    const fetchSportData = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/sports-analytics/stats/${activeSport}`);
        setSportData(res.data);
      } catch (err) {
        console.error("Failed to fetch sport data:", err);
        setSportData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchSportData();
  }, [activeSport]);

  return (
    <div className="sports-analytics-container">
      <h1 className="sports-analytics-title">Sports Analytics</h1>

      {/* Tabs */}
      <div className="sport-tabs">
        {sports.map((sport) => (
          <button
            key={sport.code}
            className={`sport-tab ${activeSport === sport.code ? "active" : ""}`}
            onClick={() => setActiveSport(sport.code)}
          >
            <span className="sport-icon">{sport.icon}</span>
            <span className="sport-name">{sport.name}</span>
          </button>
        ))}
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="loading">Loading {activeSport} data...</div>
      ) : sportData ? (
        <div className="sport-kpi-grid">
          <div className="sport-kpi-card games">
            <div className="sport-kpi-icon">🏟️</div>
            <div className="sport-kpi-value">{sportData.total_games?.toLocaleString() || 0}</div>
            <div className="sport-kpi-label">Total Games Tracked</div>
            <div className="sport-kpi-sublabel">
              {sportData.recent_games_30d || 0} in last 30 days
            </div>
          </div>

          <div className="sport-kpi-card players">
            <div className="sport-kpi-icon">👥</div>
            <div className="sport-kpi-value">{sportData.total_players?.toLocaleString() || 0}</div>
            <div className="sport-kpi-label">Players in Database</div>
            <div className="sport-kpi-sublabel">
              Across {sportData.total_teams || 0} teams
            </div>
          </div>

          <div className="sport-kpi-card stats">
            <div className="sport-kpi-icon">📊</div>
            <div className="sport-kpi-value">{sportData.total_stats?.toLocaleString() || 0}</div>
            <div className="sport-kpi-label">Stats Records</div>
            <div className="sport-kpi-sublabel">
              {sportData.total_stats && sportData.total_games 
                ? Math.round(sportData.total_stats / sportData.total_games) 
                : 0} avg per game
            </div>
          </div>

          <div className="sport-kpi-card teams">
            <div className="sport-kpi-icon">🏆</div>
            <div className="sport-kpi-value">{sportData.total_teams?.toLocaleString() || 0}</div>
            <div className="sport-kpi-label">Teams</div>
            <div className="sport-kpi-sublabel">
              {activeSport} league teams
            </div>
          </div>
        </div>
      ) : (
        <div className="no-data">No data available for {activeSport}</div>
      )}

      {/* Placeholder for future charts */}
      <div className="charts-placeholder">
        <div className="placeholder-card">
          <div className="placeholder-icon">📈</div>
          <p>Charts and visualizations coming soon...</p>
        </div>
      </div>
    </div>
  );
}

export default SportsAnalyticsPage;
