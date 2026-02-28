import React, { useRef, useCallback, useMemo, useEffect } from "react";
import api from "../services/api.js";
import { convertToUserTimezone } from "../services/timezoneService.js";
import { formatOdds } from "../services/oddsService.js";
import BetPlacementModal from "../components/BetPlacementModal.jsx";
import CustomBetBuilder from "../components/CustomBetBuilder.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import SkeletonLoader from "../components/SkeletonLoader.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import ErrorBoundary from "../components/ErrorBoundary.jsx";
import SuspenseFallback from "../components/SuspenseFallback.jsx";
import "./AAIBetsPage.css";
import { useOddsFormat } from "../hooks/useOddsFormat";
import { useLoading } from "../hooks/useLoading";
import { useError } from "../hooks/useError";
import { useMetrics } from "../hooks/useMetrics";

// Constants
const API_TIMEOUT = 240000; // 4 minutes
const MATRIX_FONT_SIZE = 14;
const MATRIX_CHARS = "01".split("");
const DEFAULT_BANKROLL = 1000;
const DEFAULT_MIN_CONFIDENCE = 60;

/**
 * Enhanced BetCard with new backend data
 */
const BetCard = React.memo(({ pick, onPlaceBet, oddsFormat }) => {
  
  const renderValueBadge = (edge, evPercent) => {
    if (!edge || edge < 2) return null;
    
    let badgeClass = 'value-badge';
    let badgeText = '';
    
    if (edge >= 5 && evPercent >= 10) {
      badgeClass += ' excellent';
      badgeText = '⭐ EXCELLENT';
    } else if (edge >= 3 && evPercent >= 5) {
      badgeClass += ' good';
      badgeText = '✅ GOOD VALUE';
    } else {
      badgeClass += ' marginal';
      badgeText = '📊 VALUE';
    }
    
    return <span className={badgeClass}>{badgeText}</span>;
  };

  const renderModelBreakdown = (models) => {
    if (!models || typeof models !== 'object') return null;
    
    const entries = Object.entries(models).filter(
      ([key]) => !['consensus', 'mean', 'confidence', 'models_used'].includes(key)
    );
    
    if (entries.length === 0) return null;
    
    return (
      <div className="model-breakdown">
        <details>
          <summary>📊 Models ({entries.length})</summary>
          <div className="model-details">
            {entries.map(([model, value]) => {
              const percentage = typeof value === 'number' 
                ? (value < 1 ? (value * 100).toFixed(1) : value.toFixed(1))
                : value;
              return (
                <div key={model} className="model-row">
                  <span className="model-label">{model}:</span>
                  <span className="model-value">{percentage}%</span>
                </div>
              );
            })}
          </div>
        </details>
      </div>
    );
  };

  const renderKellyInfo = (kellyStake, kellyFraction) => {
    if (!kellyStake && !kellyFraction) return null;
    
    return (
      <div className="kelly-info">
        <div className="kelly-row">
          <span className="kelly-label">💰 Optimal:</span>
          <span className="kelly-value">${(kellyStake || 0).toFixed(2)}</span>
        </div>
        <div className="kelly-row secondary">
          <span className="kelly-label">Kelly:</span>
          <span className="kelly-value">{((kellyFraction || 0) * 100).toFixed(2)}%</span>
        </div>
      </div>
    );
  };

  const renderRiskFactors = (riskFactors) => {
    if (!riskFactors || riskFactors.length === 0) return null;
    
    const highRisk = riskFactors.filter(r => r.severity === 'high');
    const mediumRisk = riskFactors.filter(r => r.severity === 'medium');
    
    if (highRisk.length === 0 && mediumRisk.length === 0) return null;
    
    return (
      <div className="risk-factors">
        {highRisk.map((risk, idx) => (
          <div key={idx} className="risk-item high">
            ⚠️ {risk.description}
          </div>
        ))}
        {mediumRisk.map((risk, idx) => (
          <div key={idx} className="risk-item medium">
            ⚡ {risk.description}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="aai-card">
      <div className="aai-card-header">
        <div className="aai-pick">
          {pick.pick}
          {renderValueBadge(pick.edge, pick.ev_percent)}
        </div>
        <div className="aai-confidence-column">
          <div className="aai-confidence-label">Confidence</div>
          <div className="aai-confidence">
            {(pick.combined_confidence || pick.confidence || 0).toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="aai-matchup">
        {pick.away} @ {pick.home}
      </div>

      <div className="aai-stats-grid">
        <div className="stat-item">
          <span className="stat-label">Edge:</span>
          <span className="stat-value highlight">{(pick.edge || 0).toFixed(2)}%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">EV:</span>
          <span className="stat-value highlight">{(pick.ev_percent || 0).toFixed(2)}%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Odds:</span>
          <span className="stat-value">
            {pick.odds ? formatOdds(pick.odds, oddsFormat) : 'N/A'}
          </span>
        </div>
        {pick.market_odds && (
          <div className="stat-item">
            <span className="stat-label">Market:</span>
            <span className="stat-value">
              {formatOdds(pick.market_odds, oddsFormat)}
            </span>
          </div>
        )}
      </div>

      {pick.reason && (
        <div className="aai-reason">{pick.reason}</div>
      )}

      {renderKellyInfo(pick.kelly_stake, pick.kelly_fraction)}
      {renderRiskFactors(pick.risk_factors)}
      {renderModelBreakdown(pick.models)}

      {pick.start_time && (
        <div className="aai-time">
          🕐 {convertToUserTimezone(pick.start_time, "full")}
        </div>
      )}

      <button 
        className="aai-place-bet-btn"
        onClick={() => onPlaceBet(pick)}
        aria-label={`Place bet on ${pick.pick}`}
      >
        💰 Place Bet {pick.kelly_stake && `($${pick.kelly_stake.toFixed(0)})`}
      </button>
    </div>
  );
});

BetCard.displayName = 'BetCard';

/**
 * Enhanced ParlayCard
 */
const ParlayCard = React.memo(({ parlay }) => (
  <div className="aai-card parlay-card">
    <div className="aai-card-header">
      <div className="aai-pick">
        {parlay.leg_count || parlay.legs?.length}-Leg Parlay
      </div>
      <div className="aai-confidence-column">
        <div className="aai-confidence-label">Confidence</div>
        <div className="aai-confidence">{(parlay.confidence || 0).toFixed(1)}%</div>
      </div>
    </div>

    <div className="parlay-stats">
      <div className="stat-item">
        <span className="stat-label">Odds:</span>
        <span className="stat-value highlight">
          {parlay.parlay_odds_american > 0 ? '+' : ''}{parlay.parlay_odds_american}
        </span>
      </div>
      <div className="stat-item">
        <span className="stat-label">Decimal:</span>
        <span className="stat-value">{(parlay.parlay_odds || 0).toFixed(2)}</span>
      </div>
    </div>

    <ul className="aai-legs">
      {parlay.legs?.map((leg, idx) => (
        <li key={idx}>
          <span className="leg-pick">{leg.pick}</span>
          <span className="leg-confidence">{(leg.confidence || 0).toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  </div>
));

ParlayCard.displayName = 'ParlayCard';

/**
 * Main Component
 */
function AAIBetsPage() {
  useMetrics("AAIBetsPage");
  const { error, setErrorMsg, clearError: clearError } = useError();
  const setError = (msg) => msg === null ? clearError() : setErrorMsg(msg);
  const { loading, startLoading, stopLoading } = useLoading();
  const [oddsFormat] = useOddsFormat();
  const [data, setData] = React.useState(null);
  const [hasCalculated, setHasCalculated] = React.useState(false);
  const [selectedBet, setSelectedBet] = React.useState(null);
  const [showPlacementModal, setShowPlacementModal] = React.useState(false);
  const [showCustomBuilder, setShowCustomBuilder] = React.useState(false);
  const [bankroll, setBankroll] = React.useState(DEFAULT_BANKROLL);
  const [minConfidence, setMinConfidence] = React.useState(DEFAULT_MIN_CONFIDENCE);
  const [selectedSports, setSelectedSports] = React.useState([]);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);

  // Matrix animation
  useEffect(() => {
    if (!loading || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const columns = Math.floor(canvas.width / MATRIX_FONT_SIZE);
    const drops = Array(columns).fill(1);
    
    const draw = () => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#0F0";
      ctx.font = `${MATRIX_FONT_SIZE}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const text = MATRIX_CHARS[Math.floor(Math.random() * 2)];
        ctx.fillText(text, i * MATRIX_FONT_SIZE, drops[i] * MATRIX_FONT_SIZE);
        if (drops[i] * MATRIX_FONT_SIZE > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
      animationFrameRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [loading]);

  const calculateOdds = useCallback(async () => {
    try {
      startLoading();
      clearError();
      
      const params = new URLSearchParams({
        min_confidence: minConfidence,
        bankroll: bankroll
      });
      
      if (selectedSports.length > 0) {
        params.append('sports', selectedSports.join(','));
      }
      
      const res = await api.get(
        `/api/aai-bets/refresh-and-calculate?${params.toString()}`,
        { timeout: API_TIMEOUT }
      );
      
      setData(res.data || null);
      setHasCalculated(true);
    } catch (err) {
      setErrorMsg(err.response?.data?.message || err.message || "Failed to load");
      console.error('Error:', err);
    } finally {
      stopLoading();
    }
  }, [minConfidence, bankroll, selectedSports, startLoading, stopLoading, clearError, setErrorMsg]);

  const getQuickRecommendations = useCallback(async () => {
    try {
      startLoading();
      clearError();
      
      const params = new URLSearchParams({
        min_confidence: minConfidence,
        bankroll: bankroll
      });
      
      if (selectedSports.length > 0) {
        params.append('sports', selectedSports.join(','));
      }
      
      const res = await api.get(
        `/api/aai-bets/recommendations?${params.toString()}`
      );
      
      setData(res.data || null);
      setHasCalculated(true);
    } catch (err) {
      setErrorMsg(err.response?.data?.message || err.message || "Failed");
      console.error('Error:', err);
    } finally {
      stopLoading();
    }
  }, [minConfidence, bankroll, selectedSports, startLoading, stopLoading, clearError, setErrorMsg]);

  const toggleSport = useCallback((sport) => {
    setSelectedSports(prev => 
      prev.includes(sport) ? prev.filter(s => s !== sport) : [...prev, sport]
    );
  }, []); // No external dependencies

  const openBetPlacementModal = useCallback((bet) => {
    setSelectedBet(bet);
    setShowPlacementModal(true);
  }, []); // No external dependencies

  const closeBetPlacementModal = useCallback(() => {
    setShowPlacementModal(false);
    setSelectedBet(null);
  }, []); // No external dependencies

  const openCustomBuilder = useCallback(() => setShowCustomBuilder(true), []); // No external dependencies
  const closeCustomBuilder = useCallback(() => setShowCustomBuilder(false), []); // No external dependencies

  const singles = useMemo(() => data?.singles || [], [data?.singles]);
  const freshData = useMemo(() => data?.fresh_data || {}, [data?.fresh_data]);

  const stats = useMemo(() => {
    if (!singles.length) return null;
    const highConf = singles.filter(s => (s.combined_confidence || s.confidence) >= 70).length;
    const totalEdge = singles.reduce((sum, s) => sum + (s.edge || 0), 0);
    const totalEV = singles.reduce((sum, s) => sum + (s.ev_percent || 0), 0);
    return {
      total: singles.length,
      highConfidence: highConf,
      avgEdge: (totalEdge / singles.length).toFixed(2),
      totalEV: totalEV.toFixed(2)
    };
  }, [singles]);

  if (loading) {
    return (
      <div className="matrix-container">
        <canvas ref={canvasRef} className="matrix-canvas"></canvas>
        <div className="matrix-overlay">
          <div className="matrix-text">CALCULATING ODDS</div>
          <div className="matrix-subtext">
            {hasCalculated ? 'Refreshing...' : 'Analyzing with AI models...'}
          </div>
        </div>
      </div>
    );
  }

  if (!hasCalculated) {
    return (
      <div className="aai-bets-page">
        <div className="aai-initial-state">
          <div className="aai-hero">
            <h1 className="aai-hero-title">🤖 AAI Intelligence</h1>
            <p className="aai-hero-subtitle">
              Advanced betting with 5 statistical models
              <br />
              Elo • Pythagorean • Form • Home • Vegas
              <br />
              <strong>Kelly Criterion • Expected Value • Risk Analysis</strong>
            </p>

            <div className="aai-settings">
              <div className="setting-group">
                <label>Bankroll ($)</label>
                <input
                  type="number"
                  value={bankroll}
                  onChange={(e) => setBankroll(Number(e.target.value))}
                  min="100"
                  max="100000"
                  step="100"
                />
              </div>
              <div className="setting-group">
                <label>Min Confidence (%)</label>
                <input
                  type="number"
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(Number(e.target.value))}
                  min="50"
                  max="90"
                  step="5"
                />
              </div>
            </div>

            <div className="sport-filters">
              {['NBA', 'NFL', 'NHL', 'MLB', 'NCAAB'].map(sport => (
                <button
                  key={sport}
                  className={`sport-filter-btn ${selectedSports.includes(sport) ? 'active' : ''}`}
                  onClick={() => toggleSport(sport)}
                >
                  {sport}
                </button>
              ))}
            </div>

            <button className="calculate-odds-btn" onClick={calculateOdds}>
              <span className="btn-icon">⚡</span>
              <span className="btn-text">CALCULATE ODDS</span>
              <span className="btn-icon">⚡</span>
            </button>

            <div className="aai-features">
              <div className="feature"><span>📊</span><span>5 Models</span></div>
              <div className="feature"><span>💰</span><span>Kelly Sizing</span></div>
              <div className="feature"><span>📈</span><span>Expected Value</span></div>
              <div className="feature"><span>🎯</span><span>Value Detection</span></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="aai-bets-page" role="main" aria-label="AAI Bets Page">
      <div className="aai-results">
        <div className="page-header">
          <h1>🤖 AAI Recommendations</h1>
          <p className="page-subtitle">Statistical models + Kelly Criterion</p>
          <div className="header-actions">
            <button className="quick-refresh-btn" onClick={getQuickRecommendations}>
              🔄 Quick
            </button>
            <button className="recalculate-btn" onClick={calculateOdds}>
              ⚡ Full Refresh
            </button>
          </div>
        </div>

        <div className="aai-content">
          {error && (
            <ErrorMessage
              message={error}
              type="error"
              onRetry={calculateOdds}
              onDismiss={() => setError(null)}
            />
          )}

          {!error && (
            <>
              {freshData?.success && (
                <div className="fresh-data-banner">
                  <div className="fresh-data-icon">✅</div>
                  <div className="fresh-data-info">
                    <div className="fresh-data-title">Fresh Data</div>
                    <div className="fresh-data-stats">
                      📅 {freshData.games_updated} games • 
                      🏥 {freshData.injuries_updated} injuries • 
                      ⏱️ {freshData.elapsed_seconds}s
                    </div>
                  </div>
                </div>
              )}

              {stats && (
                <div className="stats-summary">
                  <div className="stat-box">
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">Picks</div>
                  </div>
                  <div className="stat-box highlight">
                    <div className="stat-value">{stats.highConfidence}</div>
                    <div className="stat-label">High Conf</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">{stats.avgEdge}%</div>
                    <div className="stat-label">Avg Edge</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">{stats.totalEV}%</div>
                    <div className="stat-label">Total EV</div>
                  </div>
                </div>
              )}

              <div className="current-settings">
                <span>💰 ${bankroll}</span>
                <span>📊 {minConfidence}%</span>
                {selectedSports.length > 0 && <span>🏀 {selectedSports.join(', ')}</span>}
              </div>

              <div className="aai-section">
                <div className="aai-section-header">
                  <h2>Singles</h2>
                  <span className="aai-section-subtitle">{singles.length} picks</span>
                </div>
                {loading ? (
                  <div role="status" aria-live="polite">
                    <SkeletonLoader rows={6} columns={2} type="grid" width="100%" height="2em" />
                  </div>
                ) : singles.length > 0 ? (
                  <div className="aai-grid">
                    {singles.map((pick, idx) => (
                      <BetCard key={pick.game_id || idx} pick={pick} oddsFormat={oddsFormat} onPlaceBet={openBetPlacementModal} />
                    ))}
                  </div>
                ) : (
                  <div className="aai-empty" role="status" aria-live="polite">No picks. Try lower confidence.</div>
                )}
              </div>

              {data?.parlays && typeof data.parlays === 'object' && (
                Object.entries(data.parlays).map(([size, parlays]) => (
                  <div className="aai-section" key={size}>
                    <div className="aai-section-header">
                      <h2>{size.replace('_', '-')} Parlays</h2>
                      <span className="aai-section-subtitle">{parlays.length}</span>
                    </div>
                    <div className="aai-grid">
                      {parlays.map((parlay, i) => (
                        <ParlayCard 
                          key={parlay.legs.map(l => l.pick).join('-') || i}
                          parlay={parlay}
                        />
                      ))}
                    </div>
                  </div>
                ))
              )}

              <div className="aai-section">
                <button className="aai-custom-builder-btn" onClick={openCustomBuilder}>
                  🎯 Build Custom Bet
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {showPlacementModal && (
        <BetPlacementModal 
          bet={selectedBet}
          isOpen={showPlacementModal}
          onClose={closeBetPlacementModal}
          onSuccess={() => {}}
        />
      )}

      {showCustomBuilder && (
        <ErrorBoundary>
          <CustomBetBuilder 
            games={data?.upcoming_games || []}
            isOpen={showCustomBuilder}
            onClose={closeCustomBuilder}
          />
        </ErrorBoundary>
      )}
    </div>
  );
}

export default function AAIBetsPageWrapper(props) {
  return (
    <ErrorBoundary>
      <React.Suspense fallback={<SuspenseFallback message="Loading AAI bets..." />}>
        <AAIBetsPage {...props} />
      </React.Suspense>
    </ErrorBoundary>
  );
}