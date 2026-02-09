import React, { useEffect, useState } from "react";
import api from "../services/api.js";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import "./AnalyticsPage.css";

function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/analytics/summary")
      .then((res) => setSummary(res.data || null))
      .catch((err) => console.error('Failed to fetch analytics:', err))
      .finally(() => setLoading(false));
  }, []);


  if (loading) {
    return (
      <div className="analytics-container">
        <div className="loading">Loading analytics...</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="analytics-container">
        <div className="no-data">No betting data available for analysis</div>
      </div>
    );
  }

  const { roi, trends, markets, by_sport, by_bet_type, over_time, parlay_performance, streaks, ev_kelly, player_trends, team_momentum, team_splits, betting_patterns, by_source } = summary;

  // Colors for charts
  const COLORS = ['#4a90e2', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22'];
  
  // Prepare data for sport performance chart
  const sportData = Object.entries(by_sport || {})
    .filter(([sport, stats]) => stats.total > 0)
    .map(([sport, stats]) => ({
      name: sport,
      winRate: parseFloat(stats.win_rate?.toFixed(1) || 0),
      roi: parseFloat(stats.roi?.toFixed(1) || 0),
      profit: parseFloat(stats.total_profit?.toFixed(2) || 0),
      total: stats.total || 0
    }));

  // Prepare data for bet type comparison
  const betTypeData = Object.entries(by_bet_type || {})
    .filter(([type, stats]) => stats.total > 0)
    .map(([type, stats]) => ({
      name: type.toUpperCase(),
      won: stats.won || 0,
      lost: stats.lost || 0,
      pending: stats.pending || 0,
      winRate: parseFloat(stats.win_rate?.toFixed(1) || 0),
      profit: parseFloat(stats.total_profit?.toFixed(2) || 0)
    }));

  // Prepare parlay vs singles comparison
  const parlayComparison = [
    {
      name: 'Singles',
      winRate: parseFloat((parlay_performance?.singles?.win_rate || 0).toFixed(1)),
      roi: parseFloat((parlay_performance?.singles?.roi || 0).toFixed(1)),
      profit: parseFloat((parlay_performance?.singles?.profit || 0).toFixed(2))
    },
    {
      name: 'Parlays',
      winRate: parseFloat((parlay_performance?.parlays?.win_rate || 0).toFixed(1)),
      roi: parseFloat((parlay_performance?.parlays?.roi || 0).toFixed(1)),
      profit: parseFloat((parlay_performance?.parlays?.profit || 0).toFixed(2))
    }
  ];

  // Prepare win/loss distribution
  const winLossData = [
    { name: 'Won', value: trends?.wins || 0, color: '#2ecc71' },
    { name: 'Lost', value: trends?.losses || 0, color: '#e74c3c' },
    { name: 'Pending', value: trends?.pending || 0, color: '#f39c12' }
  ].filter(item => item.value > 0); // Only show categories with data

  const totalProfit = roi?.profit || 0;
  const totalStaked = roi?.total_staked || 0;
  const roiPercent = roi?.roi || 0;
  const winRate = trends?.wins && (trends.wins + trends.losses) > 0 
    ? ((trends.wins / (trends.wins + trends.losses)) * 100).toFixed(1)
    : 0;

  return (
    <div className="analytics-container">
      <h1 className="analytics-title">Betting Analytics Dashboard</h1>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card profit">
          <div className="kpi-label">Total Profit/Loss</div>
          <div className={`kpi-value ${totalProfit >= 0 ? 'positive' : 'negative'}`}>
            {totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}
          </div>
          <div className="kpi-sublabel">from ${totalStaked.toFixed(2)} staked</div>
        </div>

        <div className="kpi-card roi">
          <div className="kpi-label">ROI</div>
          <div className={`kpi-value ${roiPercent >= 0 ? 'positive' : 'negative'}`}>
            {roiPercent >= 0 ? '+' : ''}{roiPercent.toFixed(2)}%
          </div>
          <div className="kpi-sublabel">Return on Investment</div>
        </div>

        <div className="kpi-card winrate">
          <div className="kpi-label">Win Rate</div>
          <div className="kpi-value">{winRate}%</div>
          <div className="kpi-sublabel">{trends?.wins || 0}W - {trends?.losses || 0}L</div>
        </div>

        <div className="kpi-card total">
          <div className="kpi-label">Total Bets</div>
          <div className="kpi-value">{roi?.total_bets || 0}</div>
          <div className="kpi-sublabel">
            {parlay_performance?.singles?.total || 0} singles, {parlay_performance?.total_parlays || 0} parlays ({parlay_performance?.parlays?.total || 0} legs)
          </div>
        </div>

        <div className="kpi-card streak">
          <div className="kpi-label">Current Streak</div>
          <div className={`kpi-value ${streaks?.current_win_streak > 0 ? 'positive' : 'negative'}`}>
            {streaks?.current_win_streak > 0 ? `${streaks.current_win_streak}W` : `${streaks?.current_loss_streak || 0}L`}
          </div>
          <div className="kpi-sublabel">Longest: {Math.max(streaks?.longest_win_streak || 0, streaks?.longest_loss_streak || 0)} bets</div>
        </div>

        <div className="kpi-card ev">
          <div className="kpi-label">+EV Bets</div>
          <div className="kpi-value">{ev_kelly?.positive_ev_percentage || 0}%</div>
          <div className="kpi-sublabel">{ev_kelly?.ev_bets || 0} positive EV bets</div>
        </div>

        <div className="kpi-card kelly">
          <div className="kpi-label">Kelly Adherence</div>
          <div className="kpi-value">{ev_kelly?.avg_kelly_adherence || 0}%</div>
          <div className="kpi-sublabel">Average % of Kelly sizing</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        
        {/* Win/Loss Distribution */}
        <div className="chart-card">
          <h2 className="chart-title">Win/Loss Distribution</h2>
          {winLossData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={winLossData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {winLossData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-chart-data">No bet data available</div>
          )}
        </div>

        {/* Performance by Sport */}
        <div className="chart-card wide">
          <h2 className="chart-title">Performance by Sport</h2>
          {sportData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sportData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="winRate" fill="#4a90e2" name="Win Rate %" />
                <Bar dataKey="roi" fill="#2ecc71" name="ROI %" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-chart-data">No sport data available</div>
          )}
        </div>

        {/* Bet Type Performance */}
        <div className="chart-card">
          <h2 className="chart-title">Performance by Bet Type</h2>
          {betTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={betTypeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="won" fill="#2ecc71" name="Won" />
                <Bar dataKey="lost" fill="#e74c3c" name="Lost" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-chart-data">No bet type data available</div>
          )}
        </div>

        {/* Parlays vs Singles Comparison */}
        <div className="chart-card">
          <h2 className="chart-title">Parlays vs Singles</h2>
          {parlayComparison.some(p => p.roi !== 0 || p.winRate !== 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={parlayComparison}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="winRate" fill="#9b59b6" name="Win Rate %" />
                <Bar dataKey="roi" fill="#1abc9c" name="ROI %" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-chart-data">No parlay/single data available</div>
          )}
        </div>

        {/* Bet Source Performance (AAI, Custom, Manual) */}
        {by_source && Object.keys(by_source).length > 0 && (
          <div className="chart-card">
            <h2 className="chart-title">Performance by Source</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={Object.entries(by_source).map(([source, stats]) => ({
                name: source,
                winRate: parseFloat(stats.win_rate?.toFixed(1) || 0),
                roi: parseFloat(stats.roi?.toFixed(1) || 0),
                profit: parseFloat(stats.total_profit?.toFixed(2) || 0),
                total: stats.total || 0
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                  formatter={(value, name) => {
                    if (name === 'winRate' || name === 'roi') return `${value}%`;
                    if (name === 'profit') return `$${value}`;
                    return value;
                  }}
                />
                <Legend />
                <Bar dataKey="winRate" fill="#4a90e2" name="Win Rate %" />
                <Bar dataKey="roi" fill="#2ecc71" name="ROI %" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Weekly Performance Trend */}
        {over_time?.weekly && over_time.weekly.length > 0 && (
          <div className="chart-card wide">
            <h2 className="chart-title">Performance Over Time (Last 4 Weeks)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={over_time.weekly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="week" stroke="#ccc" />
                <YAxis stroke="#ccc" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Line type="monotone" dataKey="profit" stroke="#2ecc71" strokeWidth={3} name="Profit" />
                <Line type="monotone" dataKey="winRate" stroke="#4a90e2" strokeWidth={3} name="Win Rate %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* EV vs Non-EV Performance */}
        {ev_kelly && (
          <div className="chart-card">
            <h2 className="chart-title">+EV vs -EV Performance</h2>
            {ev_kelly.ev_bets > 0 || ev_kelly.negative_ev_bets > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { name: '+EV Bets', roi: ev_kelly.roi_on_positive_ev, count: ev_kelly.ev_bets, color: '#2ecc71' },
                  { name: '-EV Bets', roi: ev_kelly.roi_on_negative_ev, count: ev_kelly.negative_ev_bets, color: '#e74c3c' }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#ccc" />
                  <YAxis stroke="#ccc" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #444' }}
                    labelStyle={{ color: '#fff' }}
                    formatter={(value) => `${value.toFixed(2)}%`}
                  />
                  <Legend />
                  <Bar dataKey="roi" fill="#4a90e2" name="ROI %" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-chart-data">Not enough EV data</div>
            )}
          </div>
        )}

      </div>

      {/* Player & Team Insights */}
      {player_trends && (
        <div className="insights-section">
          <h2 className="section-title">🔥 Player Form Analysis</h2>
          
          <div className="insights-grid">
            {/* Hot Players */}
            {player_trends.hot_players?.length > 0 && (
              <div className="insight-card">
                <h3>Hot Players</h3>
                <div className="insight-list">
                  {player_trends.hot_players.map((player) => (
                    <div key={player.player_id} className="insight-item hot">
                      <div className="insight-name">{player.name}</div>
                      <div className="insight-stats">
                        <span className="badge green">+{player.trend.toFixed(1)}%</span>
                        <span className="small">{player.recent_win_rate}% recent</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Cold Players */}
            {player_trends.cold_players?.length > 0 && (
              <div className="insight-card">
                <h3>Cold Players</h3>
                <div className="insight-list">
                  {player_trends.cold_players.map((player) => (
                    <div key={player.player_id} className="insight-item cold">
                      <div className="insight-name">{player.name}</div>
                      <div className="insight-stats">
                        <span className="badge red">{player.trend.toFixed(1)}%</span>
                        <span className="small">{player.recent_win_rate}% recent</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Betting Patterns */}
      {betting_patterns && (
        <div className="insights-section">
          <h2 className="section-title">📊 Your Betting Patterns</h2>
          
          <div className="patterns-grid">
            {/* Best Sports */}
            {betting_patterns.best_sports?.length > 0 && (
              <div className="pattern-card">
                <h3>Best Sports</h3>
                <div className="pattern-list">
                  {betting_patterns.best_sports.slice(0, 5).map((sport) => (
                    <div key={sport.name} className="pattern-item">
                      <div className="pattern-name">{sport.name}</div>
                      <div className="pattern-bar">
                        <div className="bar-fill" style={{width: `${sport.win_rate}%`}}></div>
                      </div>
                      <div className="pattern-stats">{sport.win_rate}% ({sport.total})</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Best Bet Types */}
            {betting_patterns.best_bet_types?.length > 0 && (
              <div className="pattern-card">
                <h3>Best Bet Types</h3>
                <div className="pattern-list">
                  {betting_patterns.best_bet_types.slice(0, 5).map((type) => (
                    <div key={type.name} className="pattern-item">
                      <div className="pattern-name">{type.name}</div>
                      <div className="pattern-bar">
                        <div className="bar-fill" style={{width: `${type.win_rate}%`}}></div>
                      </div>
                      <div className="pattern-stats">{type.win_rate}% ({type.total})</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Best Days */}
            {betting_patterns.best_days?.length > 0 && (
              <div className="pattern-card">
                <h3>Best Days to Bet</h3>
                <div className="pattern-list">
                  {betting_patterns.best_days.slice(0, 4).map((day) => (
                    <div key={day.day} className="pattern-item">
                      <div className="pattern-name">{day.day}</div>
                      <div className="pattern-bar">
                        <div className="bar-fill" style={{width: `${day.win_rate}%`}}></div>
                      </div>
                      <div className="pattern-stats">{day.win_rate}% ({day.total})</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detailed Tables */}
      <div className="tables-section">
        <div className="table-card">
          <h2 className="table-title">Sport Performance Breakdown</h2>
          {sportData.length > 0 ? (
            <div className="table-scroll">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Sport</th>
                    <th>Total</th>
                    <th>Won</th>
                    <th>Lost</th>
                    <th>Pending</th>
                    <th>Win Rate</th>
                    <th>Profit</th>
                    <th>ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {sportData.map((sport) => (
                    <tr key={sport.name}>
                      <td><strong>{sport.name}</strong></td>
                      <td>{sport.total}</td>
                      <td className="positive">{by_sport[sport.name].won}</td>
                      <td className="negative">{by_sport[sport.name].lost}</td>
                      <td>{by_sport[sport.name].pending || 0}</td>
                      <td>{sport.winRate}%</td>
                      <td className={sport.profit >= 0 ? 'positive' : 'negative'}>
                        ${sport.profit.toFixed(2)}
                      </td>
                      <td className={sport.roi >= 0 ? 'positive' : 'negative'}>
                        {sport.roi.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="no-table-data">No sport data available</div>
          )}
        </div>

        <div className="table-card">
          <h2 className="table-title">Bet Type Breakdown</h2>
          {betTypeData.length > 0 ? (
            <div className="table-scroll">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Total</th>
                    <th>Won</th>
                    <th>Lost</th>
                    <th>Pending</th>
                    <th>Win Rate</th>
                    <th>Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {betTypeData.map((type) => (
                    <tr key={type.name}>
                      <td><strong>{type.name}</strong></td>
                      <td>{type.won + type.lost + type.pending}</td>
                      <td className="positive">{type.won}</td>
                      <td className="negative">{type.lost}</td>
                      <td>{type.pending}</td>
                      <td>{type.winRate}%</td>
                      <td className={type.profit >= 0 ? 'positive' : 'negative'}>
                        ${type.profit.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="no-table-data">No bet type data available</div>
          )}
        </div>

      </div>
    </div>
  );
}

export default AnalyticsPage;