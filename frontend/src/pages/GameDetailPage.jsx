import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';
import './GameDetailPage.css';

function GameDetailPage() {
  const { gameId } = useParams();
  const [gameData, setGameData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [statsTab, setStatsTab] = useState('home');
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState(null);

  const fetchGameDetails = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/games/${gameId}/detailed`);
      setGameData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load game details');
      console.error('Error fetching game details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (gameId) {
      fetchGameDetails();
    }
  }, [gameId]);

  const handleRefreshStats = async () => {
    try {
      setRefreshing(true);
      setRefreshMessage('Fetching player statistics...');
      const response = await api.post(`/games/${gameId}/refresh-stats`);
      
      if (response.data.success) {
        setRefreshMessage('✓ Stats updated! Reloading...');
        // Reload game details after a short delay
        setTimeout(() => {
          fetchGameDetails();
          setRefreshMessage(null);
        }, 1000);
      } else {
        setRefreshMessage(`Error: ${response.data.error}`);
      }
    } catch (err) {
      setRefreshMessage(`Error: ${err.message}`);
      console.error('Error refreshing stats:', err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="game-detail-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading game details...</p>
        </div>
      </div>
    );
  }

  if (error || !gameData) {
    return (
      <div className="game-detail-container">
        <div className="error-banner">
          <h2>⚠️ Error</h2>
          <p>{error || 'Failed to load game details'}</p>
        </div>
      </div>
    );
  }

  const game = gameData.game;
  const isLive = game.status === 'live';
  const isFinal = game.status === 'final';
  const homeTeam = game.home;
  const awayTeam = game.away;

  const getStatusBadge = () => {
    switch (game.status) {
      case 'live':
        return <span className="status-badge live">🔴 LIVE</span>;
      case 'final':
        return <span className="status-badge final">✓ FINAL</span>;
      default:
        return <span className="status-badge upcoming">📅 UPCOMING</span>;
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return 'TBA';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="game-detail-container">
      {/* Header with Game Info */}
      <div className="game-header">
        <div className="game-header-top">
          <div className="status-info">
            {getStatusBadge()}
            <span className="game-date">{formatDate(game.start_time)}</span>
            <span className="game-league">{game.league || game.sport}</span>
          </div>
        </div>

        {/* Score Section */}
        <div className="score-container">
          {/* Away Team */}
          <div className="team-card away-team">
            <div className="team-header">
              {awayTeam.logo && (
                <img src={awayTeam.logo} alt={awayTeam.team_name} className="team-logo" />
              )}
              <div className="team-info">
                <h3 className="team-name">{awayTeam.team_name}</h3>
                <p className="team-record"></p>
              </div>
            </div>
            <div className={`score ${!isFinal && !isLive ? 'pending' : ''}`}>
              {awayTeam.score !== null ? awayTeam.score : '–'}
            </div>
          </div>

          {/* VS Divider */}
          <div className="divider">
            <div className="vs-text">VS</div>
            {isLive && <div className="live-indicator">LIVE</div>}
            {!isLive && !isFinal && (
              <div className="time-info">
                <div className="time">{formatTime(game.start_time)}</div>
                {game.venue && <div className="venue">{game.venue}</div>}
              </div>
            )}
            {isFinal && (
              <div className="final-text">FINAL</div>
            )}
          </div>

          {/* Home Team */}
          <div className="team-card home-team">
            <div className={`score ${!isFinal && !isLive ? 'pending' : ''}`}>
              {homeTeam.score !== null ? homeTeam.score : '–'}
            </div>
            <div className="team-header">
              {homeTeam.logo && (
                <img src={homeTeam.logo} alt={homeTeam.team_name} className="team-logo" />
              )}
              <div className="team-info">
                <h3 className="team-name">{homeTeam.team_name}</h3>
                <p className="team-record"></p>
              </div>
            </div>
          </div>
        </div>

        {/* Game Meta Info */}
        {isLive && (
          <div className="game-meta">
            <span className="period">{game.period}</span>
            <span className="clock">{game.clock}</span>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="tabs-container">
        <div className="tabs">
          <div className="tabs-buttons">
            <button
              className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              📊 Overview
            </button>
            <button
              className={`tab ${activeTab === 'stats' ? 'active' : ''}`}
              onClick={() => setActiveTab('stats')}
            >
              📋 Statistics
            </button>
            <button
              className={`tab ${activeTab === 'bets' ? 'active' : ''}`}
              onClick={() => setActiveTab('bets')}
              style={{ 
                minWidth: 'auto', 
                flex: '0 0 auto',
                backgroundColor: 'rgba(255, 107, 107, 0.3)',
                borderRadius: '4px'
              }}
            >
              💰 Bets
            </button>
          </div>
          
          {/* Refresh Stats Button */}
          <button
            className={`refresh-stats-btn ${refreshing ? 'loading' : ''} ${
              !gameData.home_players || gameData.home_players.length === 0 ? 'highlight' : ''
            }`}
            onClick={handleRefreshStats}
            disabled={refreshing}
            title="Fetch player statistics for this game"
          >
            {refreshing ? '⟳ Fetching...' : '🔄 Update Stats'}
          </button>
        </div>
        
        {refreshMessage && (
          <div className={`refresh-message ${refreshMessage.includes('Error') ? 'error' : 'success'}`}>
            {refreshMessage}
          </div>
        )}
      </div>

      {/* Content Sections */}
      <div className="content-area">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="tab-content overview">
            <div className="team-stats-grid">
              {/* Home Team Stats */}
              <div className="team-stats-card">
                <h3 className="stats-title">{homeTeam.team_name}</h3>
                <div className="team-stats-detail">
                  {homeTeam.stats && (
                    <div className="stat-row-list">
                      <div className="stat-item">
                        <span className="stat-label">Points</span>
                        <span className="stat-value">{homeTeam.stats.points || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Rebounds</span>
                        <span className="stat-value">{homeTeam.stats.rebounds || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Assists</span>
                        <span className="stat-value">{homeTeam.stats.assists || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Steals</span>
                        <span className="stat-value">{homeTeam.stats.steals || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Blocks</span>
                        <span className="stat-value">{homeTeam.stats.blocks || '–'}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Away Team Stats */}
              <div className="team-stats-card">
                <h3 className="stats-title">{awayTeam.team_name}</h3>
                <div className="team-stats-detail">
                  {awayTeam.stats && (
                    <div className="stat-row-list">
                      <div className="stat-item">
                        <span className="stat-label">Points</span>
                        <span className="stat-value">{awayTeam.stats.points || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Rebounds</span>
                        <span className="stat-value">{awayTeam.stats.rebounds || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Assists</span>
                        <span className="stat-value">{awayTeam.stats.assists || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Steals</span>
                        <span className="stat-value">{awayTeam.stats.steals || '–'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Blocks</span>
                        <span className="stat-value">{awayTeam.stats.blocks || '–'}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Statistics Tab */}
        {activeTab === 'stats' && (
          <div className="tab-content stats">
            <div className="stats-tabs">
              <button
                className={`stats-tab ${statsTab === 'home' ? 'active' : ''}`}
                onClick={() => setStatsTab('home')}
              >
                {homeTeam.team_name}
              </button>
              <button
                className={`stats-tab ${statsTab === 'away' ? 'active' : ''}`}
                onClick={() => setStatsTab('away')}
              >
                {awayTeam.team_name}
              </button>
            </div>

            <div className="players-table">
              {statsTab === 'home' ? (
                <PlayerStatsTable players={gameData.home_players} />
              ) : (
                <PlayerStatsTable players={gameData.away_players} />
              )}
            </div>
          </div>
        )}

        {/* Bets Tab */}
        {activeTab === 'bets' && (
          <div className="tab-content bets">
            {gameData.bets && gameData.bets.length > 0 ? (
              <div className="bets-list">
                {gameData.bets.map((bet) => (
                  <BetCard key={bet.id} bet={bet} />
                ))}
              </div>
            ) : (
              <div className="no-bets-message">
                <p>No bets placed on this game yet</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Player Stats Table Component
function PlayerStatsTable({ players }) {
  if (!players || players.length === 0) {
    return <p className="no-stats">No player statistics available</p>;
  }

  // Sort by points descending
  const sortedPlayers = [...players].sort((a, b) => (b.points || 0) - (a.points || 0));

  return (
    <div className="stats-scroll-container">
      <table className="players-stats">
        <thead>
          <tr>
            <th className="player-name-col">Player</th>
            <th>MIN</th>
            <th>PTS</th>
            <th>REB</th>
            <th>AST</th>
            <th>STL</th>
            <th>BLK</th>
            <th>TO</th>
            <th>FG</th>
            <th>3PT</th>
            <th>FT</th>
          </tr>
        </thead>
        <tbody>
          {sortedPlayers.map((player) => (
            <tr key={player.player_id} className="player-row">
              <td className="player-name-cell">
                <div className="player-info">
                  {player.headshot && (
                    <img src={player.headshot} alt={player.player_name} className="player-headshot" />
                  )}
                  <div className="player-details">
                    <span className="player-name">{player.player_name}</span>
                    {player.jersey && (
                      <span className="jersey">#{player.jersey}</span>
                    )}
                    {player.position && (
                      <span className="position">{player.position}</span>
                    )}
                  </div>
                </div>
              </td>
              <td className="stat-value">{player.minutes || '–'}</td>
              <td className="stat-value pts-col">{player.points !== null ? player.points : '–'}</td>
              <td className="stat-value">{player.rebounds !== null ? player.rebounds : '–'}</td>
              <td className="stat-value">{player.assists !== null ? player.assists : '–'}</td>
              <td className="stat-value">{player.steals !== null ? player.steals : '–'}</td>
              <td className="stat-value">{player.blocks !== null ? player.blocks : '–'}</td>
              <td className="stat-value">{player.turnovers !== null ? player.turnovers : '–'}</td>
              <td className="stat-value">{player.fg || '–'}</td>
              <td className="stat-value">{player.three_pt || '–'}</td>
              <td className="stat-value">{player.ft || '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Bet Card Component
function BetCard({ bet }) {
  const getBetStatusColor = (status) => {
    switch (status) {
      case 'won':
        return 'green';
      case 'lost':
        return 'red';
      case 'pending':
        return 'blue';
      case 'void':
        return 'gray';
      default:
        return 'gray';
    }
  };

  const getBetStatusIcon = (status) => {
    switch (status) {
      case 'won':
        return '✓';
      case 'lost':
        return '✗';
      case 'pending':
        return '⏱';
      case 'void':
        return '○';
      default:
        return '?';
    }
  };

  const perf = bet.current_performance;

  return (
    <div className={`bet-card status-${getBetStatusColor(bet.status)}`}>
      <div className="bet-header">
        <div className="bet-main-info">
          <span className={`bet-status-badge ${bet.status}`}>
            {getBetStatusIcon(bet.status)} {bet.status.toUpperCase()}
          </span>
          <div className="bet-type-info">
            <h4 className="bet-type">{bet.bet_type}</h4>
            {bet.market && <p className="bet-market">{bet.market}</p>}
          </div>
        </div>
        <div className="bet-odds-info">
          <span className="odds">@{bet.odds.toFixed(2)}</span>
          <span className={`profit ${bet.profit > 0 ? 'positive' : bet.profit < 0 ? 'negative' : ''}`}>
            {bet.profit ? (bet.profit > 0 ? '+' : '') + bet.profit.toFixed(2) : '–'}
          </span>
        </div>
      </div>

      <div className="bet-details">
        <span className="selection">{bet.selection}</span>
        {bet.stat_type && <span className="stat-type">{bet.stat_type}</span>}
        <span className="stake">${bet.stake.toFixed(2)}</span>
      </div>

      {perf && (
        <div className="bet-performance">
          <div className="perf-header">
            <h5>Live Performance</h5>
          </div>
          <div className="perf-content">
            {perf.headshot && (
              <img src={perf.headshot} alt={perf.player_name} className="perf-headshot" />
            )}
            <div className="perf-details">
              <div className="perf-name">
                {perf.player_name}
                {perf.jersey && <span className="perf-jersey">#{perf.jersey}</span>}
              </div>
              <div className="perf-stat">
                <span className="perf-label">{bet.stat_type}</span>
                <span className={`perf-value ${perf.stat_value !== null ? 'has-value' : ''}`}>
                  {perf.stat_display || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {bet.raw_text && (
        <div className="bet-raw">
          <small>{bet.raw_text}</small>
        </div>
      )}
    </div>
  );
}

export default GameDetailPage;
