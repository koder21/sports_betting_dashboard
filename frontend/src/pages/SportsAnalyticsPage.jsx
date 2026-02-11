import React, { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";
import api from "../services/api.js";
import "./SportsAnalyticsPage.css";

function SportsAnalyticsPage() {
  const [activeSport, setActiveSport] = useState("ALL");
  const [sportData, setSportData] = useState(null);
  const [loading, setLoading] = useState(true);

  const sports = [
    { code: "ALL", name: "All Sports", icon: "🌐" },
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
        const endpoint = activeSport === "ALL" 
          ? "/sports-analytics/overview" 
          : `/sports-analytics/stats/${activeSport}`;
        const res = await api.get(endpoint);
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

  const COLORS = ['#00C49F', '#FF6B6B', '#4ECDC4', '#FFE66D', '#A8E6CF'];
  const CHART_COLORS = {
    primary: '#4ECDC4',
    secondary: '#FF6B6B',
    tertiary: '#FFE66D',
    grid: 'rgba(255, 255, 255, 0.1)',
    text: 'rgba(255, 255, 255, 0.8)'
  };

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.05) return null;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * Math.PI / 180);
    const y = cy + radius * Math.sin(-midAngle * Math.PI / 180);

    return (
      <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" fontSize={14} fontWeight="bold">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="sports-analytics-container">
      <div className="analytics-header">
        <div className="header-content">
          <h1 className="sports-analytics-title">
            <span className="title-icon">📊</span>
            Sports Analytics Dashboard
          </h1>
          <div className="header-subtitle">Real-time insights and performance metrics</div>
        </div>
      </div>

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
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <div className="loading-text">Loading {activeSport === "ALL" ? "all sports" : activeSport} analytics...</div>
        </div>
      ) : sportData ? (
        activeSport === "ALL" ? (
          <>
            {/* All Sports Overview KPIs */}
            <div className="sport-kpi-grid">
              <div className="sport-kpi-card games">
                <div className="kpi-header">
                  <div className="sport-kpi-icon">🌍</div>
                  <div className="kpi-trend">{sportData.sports_count || 0} sports</div>
                </div>
                <div className="sport-kpi-value">{sportData.total_games?.toLocaleString() || 0}</div>
                <div className="sport-kpi-label">Total Games Tracked</div>
                <div className="sport-kpi-sublabel">
                  Across all sports leagues
                </div>
              </div>

              <div className="sport-kpi-card players">
                <div className="kpi-header">
                  <div className="sport-kpi-icon">👥</div>
                  <div className="kpi-badge">Global</div>
                </div>
                <div className="sport-kpi-value">{sportData.total_players?.toLocaleString() || 0}</div>
                <div className="sport-kpi-label">Total Players</div>
                <div className="sport-kpi-sublabel">
                  All leagues combined
                </div>
              </div>

              <div className="sport-kpi-card stats">
                <div className="kpi-header">
                  <div className="sport-kpi-icon">📊</div>
                  <div className="kpi-metric">
                    {sportData.sports_comparison?.length || 0} leagues
                  </div>
                </div>
                <div className="sport-kpi-value">
                  {sportData.sports_comparison?.reduce((sum, s) => sum + (s.recent_games_30d || 0), 0)?.toLocaleString() || 0}
                </div>
                <div className="sport-kpi-label">Recent Games (30d)</div>
                <div className="sport-kpi-sublabel">
                  Active across all sports
                </div>
              </div>

              <div className="sport-kpi-card teams">
                <div className="kpi-header">
                  <div className="sport-kpi-icon">🏆</div>
                  <div className="kpi-percentage">Multi-sport</div>
                </div>
                <div className="sport-kpi-value">
                  {sportData.sports_comparison?.reduce((sum, s) => sum + (s.total_teams || 0), 0)?.toLocaleString() || 0}
                </div>
                <div className="sport-kpi-label">Total Teams</div>
                <div className="sport-kpi-sublabel">
                  All leagues roster
                </div>
              </div>
            </div>

            {/* Comparative Charts for All Sports */}
            <div className="charts-grid">
              {/* Games by Sport - Bar Chart */}
              <div className="chart-card">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">🏟️</span>
                    Games by Sport
                  </h3>
                  <div className="chart-subtitle">Total games tracked per league</div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={sportData.sports_comparison || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis dataKey="sport" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <YAxis stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="total_games" fill={CHART_COLORS.primary} radius={[8, 8, 0, 0]}>
                      {(sportData.sports_comparison || []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Players by Sport - Bar Chart */}
              <div className="chart-card">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">👥</span>
                    Players by Sport
                  </h3>
                  <div className="chart-subtitle">Total players in database</div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={sportData.sports_comparison || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis dataKey="sport" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <YAxis stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="total_players" fill={CHART_COLORS.secondary} radius={[8, 8, 0, 0]}>
                      {(sportData.sports_comparison || []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Average Scoring by Sport - Horizontal Bar Chart */}
              <div className="chart-card chart-card-wide">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">⚡</span>
                    Average Total Score by Sport
                  </h3>
                  <div className="chart-subtitle">Points per game comparison</div>
                </div>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={sportData.sports_comparison || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis type="number" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <YAxis 
                      dataKey="sport" 
                      type="category" 
                      stroke={CHART_COLORS.text} 
                      tick={{ fontSize: 12 }}
                      width={80}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="avg_total_score" fill={CHART_COLORS.tertiary} radius={[0, 8, 8, 0]}>
                      {(sportData.sports_comparison || []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Monthly Trend - Multi-line Chart */}
              <div className="chart-card chart-card-wide">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">📈</span>
                    Games Trend by Sport
                  </h3>
                  <div className="chart-subtitle">12-month activity comparison</div>
                </div>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={sportData.monthly_trend || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                    <XAxis 
                      dataKey="month" 
                      stroke={CHART_COLORS.text}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="NBA" stroke={COLORS[0]} strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="NFL" stroke={COLORS[1]} strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="NCAAB" stroke={COLORS[2]} strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="NHL" stroke={COLORS[3]} strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="EPL" stroke={COLORS[4]} strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Home Win Percentage - Radar Chart */}
              <div className="chart-card">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">🏠</span>
                    Home Advantage by Sport
                  </h3>
                  <div className="chart-subtitle">Home win percentage comparison</div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={sportData.sports_comparison?.map(s => ({
                    sport: s.sport,
                    home_win_pct: s.home_win_percentage || 0
                  })) || []}>
                    <PolarGrid stroke={CHART_COLORS.grid} />
                    <PolarAngleAxis dataKey="sport" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                    <PolarRadiusAxis stroke={CHART_COLORS.grid} angle={90} domain={[0, 100]} />
                    <Radar name="Home Win %" dataKey="home_win_pct" stroke={CHART_COLORS.primary} fill={CHART_COLORS.primary} fillOpacity={0.6} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Activity Distribution - Pie Chart */}
              <div className="chart-card">
                <div className="chart-header">
                  <h3 className="chart-title">
                    <span className="chart-icon">📊</span>
                    Recent Activity Distribution
                  </h3>
                  <div className="chart-subtitle">Last 30 days by sport</div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={sportData.sports_comparison?.map(s => ({
                        name: s.sport,
                        value: s.recent_games_30d || 0
                      })) || []}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={renderCustomizedLabel}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {(sportData.sports_comparison || []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        ) : (
          <>
          <div className="sport-kpi-grid">
            <div className="sport-kpi-card games">
              <div className="kpi-header">
                <div className="sport-kpi-icon">🏟️</div>
                <div className="kpi-trend">+{sportData.recent_games_30d || 0}</div>
              </div>
              <div className="sport-kpi-value">{sportData.total_games?.toLocaleString() || 0}</div>
              <div className="sport-kpi-label">Total Games Tracked</div>
              <div className="sport-kpi-sublabel">
                {sportData.recent_games_30d || 0} in last 30 days
              </div>
            </div>

            <div className="sport-kpi-card players">
              <div className="kpi-header">
                <div className="sport-kpi-icon">👥</div>
                <div className="kpi-badge">{sportData.total_teams || 0} teams</div>
              </div>
              <div className="sport-kpi-value">{sportData.total_players?.toLocaleString() || 0}</div>
              <div className="sport-kpi-label">Players in Database</div>
              <div className="sport-kpi-sublabel">
                Avg {Math.round((sportData.total_players || 0) / (sportData.total_teams || 1))} per team
              </div>
            </div>

            <div className="sport-kpi-card stats">
              <div className="kpi-header">
                <div className="sport-kpi-icon">📊</div>
                <div className="kpi-metric">
                  {sportData.avg_total_score?.toFixed(1) || 0} PPG
                </div>
              </div>
              <div className="sport-kpi-value">{sportData.total_stats?.toLocaleString() || 0}</div>
              <div className="sport-kpi-label">Stats Records</div>
              <div className="sport-kpi-sublabel">
                {sportData.total_stats && sportData.total_games 
                  ? Math.round(sportData.total_stats / sportData.total_games) 
                  : 0} avg per game
              </div>
            </div>

            <div className="sport-kpi-card teams">
              <div className="kpi-header">
                <div className="sport-kpi-icon">🏆</div>
                <div className="kpi-percentage">
                  {sportData.home_wins && sportData.total_games 
                    ? `${((sportData.home_wins / sportData.total_games) * 100).toFixed(1)}%` 
                    : '0%'} home
                </div>
              </div>
              <div className="sport-kpi-value">{sportData.total_teams?.toLocaleString() || 0}</div>
              <div className="sport-kpi-label">Active Teams</div>
              <div className="sport-kpi-sublabel">
                {activeSport} league roster
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="charts-grid">
            {/* Home vs Away Performance - Pie Chart */}
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">
                  <span className="chart-icon">🏠</span>
                  Home vs Away Performance
                </h3>
                <div className="chart-subtitle">Win distribution analysis</div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Home Wins', value: sportData.home_wins || 0 },
                      { name: 'Away Wins', value: sportData.away_wins || 0 }
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={renderCustomizedLabel}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    <Cell fill={CHART_COLORS.primary} />
                    <Cell fill={CHART_COLORS.secondary} />
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Monthly Games Trend - Area Chart */}
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">
                  <span className="chart-icon">📈</span>
                  Games Over Time
                </h3>
                <div className="chart-subtitle">12-month trend analysis</div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={sportData.monthly_games || []}>
                  <defs>
                    <linearGradient id="colorGames" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis 
                    dataKey="month" 
                    stroke={CHART_COLORS.text}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="games" 
                    stroke={CHART_COLORS.primary} 
                    fillOpacity={1} 
                    fill="url(#colorGames)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Top Teams - Horizontal Bar Chart */}
            <div className="chart-card chart-card-wide">
              <div className="chart-header">
                <h3 className="chart-title">
                  <span className="chart-icon">⭐</span>
                  Top Scoring Teams
                </h3>
                <div className="chart-subtitle">Last 30 days average points</div>
              </div>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={sportData.top_teams || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis type="number" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                  <YAxis 
                    dataKey="team" 
                    type="category" 
                    stroke={CHART_COLORS.text} 
                    tick={{ fontSize: 11 }}
                    width={120}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="avg_score" fill={CHART_COLORS.primary} radius={[0, 8, 8, 0]}>
                    {(sportData.top_teams || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Score Distribution - Bar Chart */}
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">
                  <span className="chart-icon">📊</span>
                  Total Score Distribution
                </h3>
                <div className="chart-subtitle">Points per game breakdown</div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={sportData.score_distribution || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis dataKey="range" stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                  <YAxis stroke={CHART_COLORS.text} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="count" fill={CHART_COLORS.tertiary} radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Scoring Comparison - Radar Chart */}
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">
                  <span className="chart-icon">🎯</span>
                  Scoring Metrics
                </h3>
                <div className="chart-subtitle">Multi-dimensional analysis</div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={[
                  { metric: 'Home Avg', value: sportData.avg_home_score || 0, fullMark: 150 },
                  { metric: 'Away Avg', value: sportData.avg_away_score || 0, fullMark: 150 },
                  { metric: 'Total Avg', value: sportData.avg_total_score || 0, fullMark: 250 },
                  { metric: 'Home Wins', value: (sportData.home_wins || 0) / 10, fullMark: 100 },
                  { metric: 'Away Wins', value: (sportData.away_wins || 0) / 10, fullMark: 100 }
                ]}>
                  <PolarGrid stroke={CHART_COLORS.grid} />
                  <PolarAngleAxis dataKey="metric" stroke={CHART_COLORS.text} tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis stroke={CHART_COLORS.grid} />
                  <Radar name={activeSport} dataKey="value" stroke={CHART_COLORS.primary} fill={CHART_COLORS.primary} fillOpacity={0.6} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px'
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
          </>
        )
      ) : (
        <div className="no-data">
          <div className="no-data-icon">📭</div>
          <div className="no-data-text">No data available for {activeSport}</div>
          <div className="no-data-subtext">Try selecting a different sport</div>
        </div>
      )}
    </div>
  );
}

export default SportsAnalyticsPage;
