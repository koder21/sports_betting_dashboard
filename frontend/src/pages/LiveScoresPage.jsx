import React, { useRef } from 'react';
import './LiveScoresPage.css';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { convertToUserTimezone } from '../services/timezoneService';
import { useLoading } from '../hooks/useLoading';
import { useError } from '../hooks/useError';
import { useMetrics } from '../hooks/useMetrics';

function LiveScoresPage() {
  useMetrics('LiveScoresPage');
  const { loading, startLoading, stopLoading } = useLoading();
  const { error, setErrorMsg, clearError } = useError();
  const [sportFilter, setSportFilter] = React.useState('ALL');
  const SPORT_OPTIONS = ['ALL', 'NBA', 'NFL', 'MLB', 'NHL', 'NCAAB', 'NCAAF', 'SOCCER'];
  const [games, setGames] = React.useState([]);
  const [upcomingGames, setUpcomingGames] = React.useState([]);
  const [lastUpdated, setLastUpdated] = React.useState(null);
  const [pendingBetsByGame, setPendingBetsByGame] = React.useState({});
  const [teamMomentum, setTeamMomentum] = React.useState({});
  const [collapsedSections, setCollapsedSections] = React.useState({});
  const [refreshing, setRefreshing] = React.useState(false);
  const [schedulerEnabled, setSchedulerEnabled] = React.useState(true); // assume on until confirmed off
  const prevScores = useRef({});
  const navigate = useNavigate();

  const buildPendingMap = React.useCallback((betsList) => {
    const map = {};
    betsList
      .filter(
        (b) => (b.status === 'pending' || b.status === 'won' || b.status === 'lost') && b.game_id
      )
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
        if (b.status === 'won' || b.status === 'lost') {
          const result = b.status === 'won' ? 'W' : 'L';
          map[b.game_id].finished.push(result);
        }
      });
    return map;
  }, []);

  const teamMatchesSelection = (teamName, selections) => {
    if (!teamName || !selections || selections.length === 0) return false;
    const teamTokens = String(teamName)
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 2);
    return selections.some((sel) => teamTokens.some((t) => sel.includes(t)));
  };

  const loadLive = React.useCallback(async () => {
    try {
      startLoading();
      const res = await api.get('/api/live');
      const upcomingRes = await api.get('/api/live/upcoming');
      const betsRes = await api.get('/api/bets/all');
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
      setErrorMsg(null);
    } catch (err) {
      setErrorMsg('Failed to load live scores: ' + (err?.message || err));
      console.error('Failed to load live scores:', err);
    } finally {
      stopLoading();
    }
  }, [startLoading, stopLoading, setErrorMsg, buildPendingMap]);

  const refreshLive = React.useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await api.post('/api/live/refresh');
      await loadLive();
    } catch (err) {
      console.error('Live refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  }, [refreshing, loadLive]);

  const loadMomentum = React.useCallback(async () => {
    try {
      // Load team momentum less frequently (every 60s) as it's expensive to compute
      const momentumRes = await api.get('/api/analytics/team-momentum');
      const momentum = momentumRes?.data || {};
      setTeamMomentum(momentum);
    } catch (err) {
      console.error('Failed to load team momentum:', err);
    }
  }, []);

  // Prevent multiple intervals/remounts
  React.useEffect(() => {
    loadLive();
    loadMomentum();
    api
      .get('/api/live/config')
      .then((res) => setSchedulerEnabled(res.data?.scheduler_enabled !== false))
      .catch(() => {});
    const handleStorage = (e) => {
      if (e.key === 'user_timezone_preference') {
        setLastUpdated(Date.now());
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener('storage', handleStorage);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadMomentum]);

  const formatTime = (date) => {
    if (!date) return '';
    return convertToUserTimezone(date, 'time-with-tz');
  };

  const getStatusClass = (status) => {
    if (status === 'ongoing') return 'status-live';
    if (status === 'completed') return 'status-final';
    return 'status-scheduled';
  };

  const getMomentumStatus = (teamId) => {
    if (!teamId || !teamMomentum[teamId]) return null;
    return teamMomentum[teamId].momentum_status;
  };

  const SPORT_ORDER = ['NFL', 'NBA', 'NCAAF', 'NHL', 'NCAAB', 'MLB', 'SOCCER'];

  // Separate live games with active bets (sticky at top)

  // Always show all live games, regardless of pending bets
  const now = new Date();
  // Only show finished games from last 36 hours
  const finishedGames = games.filter((g) => {
    if (g.status !== 'completed') return false;
    const endTime = g.start_time ? new Date(g.start_time) : null;
    if (!endTime) return false;
    return now - endTime <= 36 * 60 * 60 * 1000; // 36 hours in ms
  });

  // Only show upcoming games within next 24 hours
  const sortedUpcomingGames = (upcomingGames || [])
    .filter((g) => {
      const status = String(g.status || '').toLowerCase();
      const startTime = g.start_time ? new Date(g.start_time) : null;
      if (!startTime) return false;
      // Accept if scheduled and within next 24 hours
      return (
        (status === 'scheduled' ||
          (!status && startTime > now) ||
          (status !== 'ongoing' && status !== 'completed' && startTime > now)) &&
        startTime - now <= 24 * 60 * 60 * 1000 &&
        startTime - now >= 0
      );
    })
    .sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time) : new Date(0);
      const bTime = b.start_time ? new Date(b.start_time) : new Date(0);
      return aTime - bTime;
    });

  // For sticky section, show games with any attached bets (pending, won, lost)
  const liveGamesWithBets = games.filter((g) => {
    if (g.status !== 'ongoing') return false;
    const betInfo = pendingBetsByGame[g.game_id];
    // Show if any bets (pending, won, lost) are attached
    return (
      betInfo &&
      (betInfo.selections.length > 0 || betInfo.players.length > 0 || betInfo.finished.length > 0)
    );
  });
  const liveGamesWithoutBets = games.filter(
    (g) =>
      g.status === 'ongoing' && !liveGamesWithBets.some((betGame) => betGame.game_id === g.game_id)
  );

  const groupGamesBySport = (gamesList) => {
    const grouped = {};
    gamesList.forEach((g) => {
      const sport = (g.sport || 'OTHER').toUpperCase();
      if (!grouped[sport]) {
        grouped[sport] = [];
      }
      grouped[sport].push(g);
    });

    const sorted = {};
    SPORT_ORDER.forEach((sport) => {
      if (grouped[sport]) {
        sorted[sport] = grouped[sport];
      }
    });
    Object.keys(grouped).forEach((sport) => {
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
    // Filter by sport
    let filteredGames = gamesList;
    if (sportFilter !== 'ALL') {
      filteredGames = filteredGames.filter((g) => (g.sport || '').toUpperCase() === sportFilter);
    }
    // Group by sport
    const grouped = groupGamesBySport(filteredGames);
    return (
      <div className="games-section">
        <h2 className="section-title">{title}</h2>
        <div className="filter-row">
          <label className="filter-label">Sport:</label>
          <select
            className="filter-select"
            value={sportFilter}
            onChange={(e) => setSportFilter(e.target.value)}
          >
            {SPORT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div className="sport-table-container">
          {Object.keys(grouped).map((sport) => (
            <div key={sport} className="sport-section">
              <button
                className="collapse-toggle"
                onClick={() => setCollapsedSections((prev) => ({ ...prev, [sport]: !prev[sport] }))}
                aria-expanded={!collapsedSections[sport]}
                aria-controls={`games-table-${sport}`}
              >
                {collapsedSections[sport] ? `▶ ${sport}` : `▼ ${sport}`}
              </button>
              {!collapsedSections[sport] && (
                <table className="table games-table" id={`games-table-${sport}`}>
                  <thead>
                    <tr>
                      <th>Sport</th>
                      <th>Matchup</th>
                      <th>Bets</th>
                      {title === '✅ Finished Games' && <th>Score</th>}
                      {title !== '✅ Finished Games' && title !== '📅 Upcoming Games' && (
                        <th>Score</th>
                      )}
                      {title !== '✅ Finished Games' && title !== '📅 Upcoming Games' && (
                        <th>Clock</th>
                      )}
                      {title !== '✅ Finished Games' && title !== '📅 Upcoming Games' && (
                        <th>Period</th>
                      )}
                      {title === '📅 Upcoming Games' && <th>Start Time</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {grouped[sport].map((g) => {
                      const pendingInfo = pendingBetsByGame[g.game_id];
                      const selections = pendingInfo?.selections || [];
                      const players = pendingInfo?.players || [];
                      const finished = pendingInfo?.finished || [];
                      const hasHomeBet = teamMatchesSelection(g.home_team, selections);
                      const hasAwayBet = teamMatchesSelection(g.away_team, selections);
                      const hasPlayerBet = players.length > 0;
                      const homeMomentum = getMomentumStatus(g.home_team_id);
                      const awayMomentum = getMomentumStatus(g.away_team_id);
                      let betsContent = null;
                      if (hasHomeBet || hasAwayBet || hasPlayerBet || finished.length > 0) {
                        betsContent = (
                          <div className="bet-badges">
                            {hasHomeBet && <span className="bet-badge home">Home</span>}
                            {hasAwayBet && <span className="bet-badge away">Away</span>}
                            {hasPlayerBet && (
                              <span className="bet-badge player" title={players.join(', ')}>
                                Player ({players.length})
                              </span>
                            )}
                            {finished.length > 0 && (
                              <>
                                {finished.map((result, idx) => (
                                  <span
                                    key={idx}
                                    className={`bet-badge ${result === 'W' ? 'win' : 'loss'}`}
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
                          className="game-row"
                          style={{ cursor: 'pointer' }}
                          onClick={() => navigate(`/games/${g.game_id}/details`)}
                        >
                          <td>{g.sport}</td>
                          <td>
                            <div className="matchup-container">
                              <span className="team-name">
                                {g.home_logo && (
                                  <img
                                    src={g.home_logo}
                                    className="team-logo"
                                    alt=""
                                    onError={(e) => {
                                      e.target.onerror = null;
                                      e.target.src =
                                        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" font-size="10" text-anchor="middle" fill="%23666" dy=".3em">?</text></svg>';
                                    }}
                                  />
                                )}
                                {g.home_team}
                                {homeMomentum === 'FIRE' && (
                                  <span className="momentum-badge fire">🔥</span>
                                )}
                                {homeMomentum === 'FREEZING' && (
                                  <span className="momentum-badge freezing">🧊</span>
                                )}
                              </span>
                              <span className="vs-text"> vs </span>
                              <span className="team-name">
                                {g.away_logo && (
                                  <img
                                    src={g.away_logo}
                                    className="team-logo"
                                    alt=""
                                    onError={(e) => {
                                      e.target.onerror = null;
                                      e.target.src =
                                        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" font-size="10" text-anchor="middle" fill="%23666" dy=".3em">?</text></svg>';
                                    }}
                                  />
                                )}
                                {g.away_team}
                                {awayMomentum === 'FIRE' && (
                                  <span className="momentum-badge fire">🔥</span>
                                )}
                                {awayMomentum === 'FREEZING' && (
                                  <span className="momentum-badge freezing">🧊</span>
                                )}
                              </span>
                            </div>
                          </td>
                          <td>{betsContent}</td>
                          {title === '✅ Finished Games' && (
                            <td>
                              <span className={g.homeScoreChanged ? 'score flash' : 'score'}>
                                {g.home_score}
                              </span>
                              {' - '}
                              <span className={g.awayScoreChanged ? 'score flash' : 'score'}>
                                {g.away_score}
                              </span>
                            </td>
                          )}
                          {title !== '✅ Finished Games' && title !== '📅 Upcoming Games' && (
                            <td>
                              <span className={g.homeScoreChanged ? 'score flash' : 'score'}>
                                {g.home_score}
                              </span>
                              {' - '}
                              <span className={g.awayScoreChanged ? 'score flash' : 'score'}>
                                {g.away_score}
                              </span>
                            </td>
                          )}
                          {title !== '✅ Finished Games' && title !== '📅 Upcoming Games' && (
                            <>
                              <td>{g.clock || '-'}</td>
                              <td>{g.period || '-'}</td>
                            </>
                          )}
                          {title === '📅 Upcoming Games' && (
                            <td>
                              {g.start_time ? (
                                <div className="game-time-stack">
                                  <span className="game-date">
                                    {convertToUserTimezone(g.start_time, 'date')}
                                  </span>
                                  <span className="game-time">
                                    {convertToUserTimezone(g.start_time, 'time-with-tz')}
                                  </span>
                                </div>
                              ) : (
                                '-'
                              )}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      <div className="live-page" role="main" aria-label="Live Scores Page">
        {error && (
          <div className="error-message" role="alert">
            <span>{error}</span>
            <button onClick={clearError} className="error-dismiss">
              Dismiss
            </button>
          </div>
        )}
        <h1>Live Scores</h1>
        <div className="live-header-row">
          {lastUpdated && <div className="updated-text">Updated at {formatTime(lastUpdated)}</div>}
          <div className="refresh-hint-row">
            {schedulerEnabled ? (
              <div className="refresh-hint">Auto-refreshing every 2 minutes</div>
            ) : (
              <button
                className="refresh-btn"
                onClick={refreshLive}
                disabled={refreshing || loading}
                title="Fetch latest live scores from ESPN now"
              >
                {refreshing ? 'Refreshing…' : '⟳ Refresh Live Games'}
              </button>
            )}
          </div>
        </div>
        {loading && (
          <p role="status" aria-live="polite">
            Loading live games…
          </p>
        )}
        {/* Always render in this order: Live games with bets, other live games, upcoming games, finished games */}
        {!loading && liveGamesWithBets.length > 0 && (
          <div className="sticky-games-section">
            <h2 className="sticky-games-title">📌 Live Games with Active Bets</h2>
            <div className="sticky-games-container">
              {liveGamesWithBets.map((g) =>
                (() => {
                  const pendingInfo = pendingBetsByGame[g.game_id];
                  const selections = pendingInfo?.selections || [];
                  const players = pendingInfo?.players || [];
                  const finished = pendingInfo?.finished || [];
                  const hasHomeBet = teamMatchesSelection(g.home_team, selections);
                  const hasAwayBet = teamMatchesSelection(g.away_team, selections);
                  const hasPlayerBet = players.length > 0;
                  // LOG game object and possible keys
                  console.log('Game object:', g);
                  console.log('home_team_id:', g.home_team_id);
                  console.log('away_team_id:', g.away_team_id);
                  console.log('sport:', g.sport);
                  // LOG momentum lookup keys
                  console.log('Momentum lookup home:', g.home_team_id);
                  console.log('Momentum lookup away:', g.away_team_id);
                  const homeMomentum = getMomentumStatus(g.home_team_id);
                  const awayMomentum = getMomentumStatus(g.away_team_id);
                  return (
                    <table key={g.game_id} className="table live-table sticky-game-table">
                      <tbody>
                        <tr
                          className={`game-row ${getStatusClass(g.status)}`}
                          onClick={() => navigate(`/games/${g.game_id}/details`)}
                        >
                          <td>
                            <div className="matchup-container">
                              <span className="team-name">
                                {g.home_logo && (
                                  <img
                                    src={g.home_logo}
                                    className="team-logo"
                                    alt=""
                                    onError={(e) => {
                                      e.target.onerror = null;
                                      e.target.src =
                                        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" font-size="10" text-anchor="middle" fill="%23666" dy=".3em">?</text></svg>';
                                    }}
                                  />
                                )}
                                {g.home_team}
                                {homeMomentum === 'FIRE' && (
                                  <span className="momentum-badge fire">🔥</span>
                                )}
                                {homeMomentum === 'FREEZING' && (
                                  <span className="momentum-badge freezing">🧊</span>
                                )}
                              </span>
                              <span className="vs-text"> vs </span>
                              <span className="team-name">
                                {g.away_logo && (
                                  <img
                                    src={g.away_logo}
                                    className="team-logo"
                                    alt=""
                                    onError={(e) => {
                                      e.target.onerror = null;
                                      e.target.src =
                                        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" font-size="10" text-anchor="middle" fill="%23666" dy=".3em">?</text></svg>';
                                    }}
                                  />
                                )}
                                {g.away_team}
                                {awayMomentum === 'FIRE' && (
                                  <span className="momentum-badge fire">🔥</span>
                                )}
                                {awayMomentum === 'FREEZING' && (
                                  <span className="momentum-badge freezing">🧊</span>
                                )}
                              </span>
                            </div>
                          </td>
                          <td>
                            <div className="bet-badges">
                              {hasHomeBet && <span className="bet-badge home">Home</span>}
                              {hasAwayBet && <span className="bet-badge away">Away</span>}
                              {hasPlayerBet && (
                                <span className="bet-badge player" title={players.join(', ')}>
                                  Player ({players.length})
                                </span>
                              )}
                              {finished.length > 0 && (
                                <>
                                  {finished.map((result, idx) => (
                                    <span
                                      key={idx}
                                      className={`bet-badge ${result === 'W' ? 'win' : 'loss'}`}
                                    >
                                      {result}
                                    </span>
                                  ))}
                                </>
                              )}
                            </div>
                          </td>
                          <td>
                            <span className={g.homeScoreChanged ? 'score flash' : 'score'}>
                              {g.home_score}
                            </span>
                            {' - '}
                            <span className={g.awayScoreChanged ? 'score flash' : 'score'}>
                              {g.away_score}
                            </span>
                          </td>
                          <td>{g.clock || '-'}</td>
                          <td>{g.period || '-'}</td>
                        </tr>
                      </tbody>
                    </table>
                  );
                })()
              )}
            </div>
          </div>
        )}
        {!loading && liveGamesWithoutBets.length > 0 && (
          <>{renderGamesTable(liveGamesWithoutBets, '🔴 Live Games')}</>
        )}
        {!loading && sortedUpcomingGames.length > 0 && (
          <>{renderGamesTable(sortedUpcomingGames, '📅 Upcoming Games')}</>
        )}
        {!loading && finishedGames.length > 0 && (
          <>{renderGamesTable(finishedGames, '✅ Finished Games')}</>
        )}
      </div>
    </>
  );
}

export default LiveScoresPage;
