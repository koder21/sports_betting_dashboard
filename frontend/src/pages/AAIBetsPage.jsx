import React, { useEffect, useState, useRef } from "react";
import api from "../services/api.js";
import { convertToUserTimezone } from "../services/timezoneService.js";
import BetPlacementModal from "../components/BetPlacementModal.jsx";
import CustomBetBuilder from "../components/CustomBetBuilder.jsx";
import ErrorBoundary from "../components/ErrorBoundary.jsx";
import "./AAIBetsPage.css";

function AAIBetsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasCalculated, setHasCalculated] = useState(false);
  const [selectedBet, setSelectedBet] = useState(null);
  const [showPlacementModal, setShowPlacementModal] = useState(false);
  const [showCustomBuilder, setShowCustomBuilder] = useState(false);
  const canvasRef = useRef(null);
  
  const modelOptions = [
    { id: "all", label: "All" },
    { id: "vegas", label: "Vegas" },
    { id: "elo", label: "Elo" },
    { id: "ml", label: "ML" },
    { id: "kelly", label: "Kelly" },
  ];
  const [selectedModels, setSelectedModels] = useState(["all"]);

  // Matrix effect
  useEffect(() => {
    if (!loading || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    
    // Set canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops = Array(columns).fill(1);

    const matrix = "01"; // Binary characters
    const matrixChars = matrix.split("");

    let animationId;
    
    const draw = () => {
      // Semi-transparent black to create trail effect
      ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = "#0F0"; // Green text
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const text = matrixChars[Math.floor(Math.random() * matrixChars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);

        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [loading]);

  const calculateOdds = async () => {
    try {
      setLoading(true);
      setError(null);
      const modelsParam = selectedModels.includes("all")
        ? "all"
        : selectedModels.join(",");
      
      // Call the fresh data scraping + calculation endpoint with extended timeout
      // This endpoint scrapes ALL fresh data (games, injuries, weather) so it needs time
      const res = await api.get(
        `/aai-bets/refresh-and-calculate?models=${modelsParam}`,
        { timeout: 240000 } // 4 minute timeout for complete data collection
      );
      setData(res.data || null);
      setHasCalculated(true);
    } catch (err) {
      setError("Failed to load recommendations");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleModel = (modelId) => {
    if (modelId === "all") {
      setSelectedModels(["all"]);
      return;
    }

    setSelectedModels((prev) => {
      const hasAll = prev.includes("all");
      const base = hasAll ? [] : prev.slice();
      if (base.includes(modelId)) {
        const next = base.filter((m) => m !== modelId);
        return next.length ? next : ["all"];
      }
      return [...base, modelId];
    });
  };

  const renderExternalOdds = (odds) => {
    if (!odds || Object.keys(odds).length === 0) return null;
    const modelCount = Object.keys(odds).filter((key) => key !== "mean").length;
    return (
      <div className="aai-external-odds">
        <details>
          <summary>External Models ({modelCount})</summary>
          <div className="odds-breakdown">
            {Object.entries(odds).map(([model, prob]) => (
              <div key={model} className="odds-item">
                <span className="model-name">{model}:</span>
                <span className="model-prob">{prob}%</span>
              </div>
            ))}
          </div>
        </details>
      </div>
    );
  };

  const openBetPlacementModal = (bet) => {
    setSelectedBet(bet);
    setShowPlacementModal(true);
  };

  const closeBetPlacementModal = () => {
    setShowPlacementModal(false);
    setSelectedBet(null);
  };

  const handleBetPlacedSuccess = (result) => {
    // Show success message
    console.log("Bet placed successfully:", result);
    // Could add toast notification here
  };

  const openCustomBuilder = () => {
    setShowCustomBuilder(true);
  };

  const closeCustomBuilder = (result) => {
    setShowCustomBuilder(false);
    if (result) {
      console.log("Custom bet placed:", result);
      // Could add toast notification here
    }
  };

  return (
    <div className="aai-bets-page">
      {/* Matrix loading effect */}
      {loading && (
        <div className="matrix-container">
          <canvas ref={canvasRef} className="matrix-canvas"></canvas>
          <div className="matrix-overlay">
            <div className="matrix-text">CALCULATING ODDS</div>
            <div className="matrix-subtext">Analyzing data streams...</div>
          </div>
        </div>
      )}

      {/* Initial state - just the button */}
      {!loading && !hasCalculated && (
        <div className="aai-initial-state">
          <div className="aai-hero">
            <h1 className="aai-hero-title">🤖 AAI Intelligence</h1>
            <p className="aai-hero-subtitle">Advanced betting recommendations powered by real-time data and AI models.<br />(not recommended to use this page yet, or ever, as AI is normally better at this and prop bets are hard with free APIs. Use the Bets page.</p>
            <button className="calculate-odds-btn" onClick={calculateOdds}>
              <span className="btn-icon">⚡</span>
              <span className="btn-text">CALCULATE ODDS</span>
              <span className="btn-icon">⚡</span>
            </button>
            <div className="aai-features">
              <div className="feature">
                <span className="feature-icon">📊</span>
                <span>Live Form Analysis</span>
              </div>
              <div className="feature">
                <span className="feature-icon">🌦️</span>
                <span>Weather Impact</span>
              </div>
              <div className="feature">
                <span className="feature-icon">🏥</span>
                <span>Injury Tracking</span>
              </div>
              <div className="feature">
                <span className="feature-icon">🎯</span>
                <span>Multi-Model Consensus</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results after calculation */}
      {!loading && hasCalculated && (
        <div className="aai-results">
          <div className="page-header">
            <h1>🤖 AAI Bets</h1>
            <p className="page-subtitle">Data-driven singles and parlays for today</p>
            <button className="recalculate-btn" onClick={calculateOdds}>
              🔄 Recalculate
            </button>
          </div>

          <div className="aai-content">
            {error && <div className="aai-error">{error}</div>}

            {!error && (
              <>
                {/* Fresh Data Summary */}
                {data?.fresh_data && (
                  <div className="fresh-data-banner">
                    <div className="fresh-data-icon">✅</div>
                    <div className="fresh-data-info">
                      <div className="fresh-data-title">Fresh Data Loaded</div>
                      <div className="fresh-data-stats">
                        📅 {data.fresh_data.games_updated} games • 
                        🏥 {data.fresh_data.injuries_updated} injuries • 
                        🌦️ {data.fresh_data.weather_forecasts} forecasts • 
                        ⏱️ {data.fresh_data.elapsed_seconds}s
                      </div>
                    </div>
                  </div>
                )}

                <div className="aai-disclaimer">
                  {data?.disclaimer ||
                    "These recommendations blend team form with external models. Not financial advice."}
                </div>

                <div className="aai-model-toggles">
                  <div className="aai-model-label">Models</div>
                  <div className="aai-model-options">
                    {modelOptions.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        className={
                          selectedModels.includes(option.id)
                            ? "aai-model-btn active"
                            : "aai-model-btn"
                        }
                        onClick={() => toggleModel(option.id)}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Singles */}
                <div className="aai-section">
                  <div className="aai-section-header">
                    <h2>Singles</h2>
                    <span className="aai-section-subtitle">Highest confidence picks</span>
                  </div>
              {data?.singles?.length ? (
                <div className="aai-grid">
                  {data.singles.map((pick) => (
                    <div key={`${pick.game_id}-${pick.pick}`} className="aai-card">
                      <div className="aai-card-header">
                        <div className="aai-pick">{pick.pick}</div>
                        <div className="aai-confidence-column">
                          <div className="aai-confidence-label">Form</div>
                          <div className="aai-confidence">{pick.confidence}%</div>
                          {pick.combined_confidence && pick.combined_confidence !== pick.confidence && (
                            <>
                              <div className="aai-confidence-label">Blended</div>
                              <div className="aai-confidence-combined">{pick.combined_confidence}%</div>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="aai-matchup">
                        {pick.away} @ {pick.home}
                      </div>
                      <div className="aai-reason">{pick.reason}</div>
                      {pick.external_odds && renderExternalOdds(pick.external_odds)}
                      {pick.start_time && (
                        <div className="aai-time">{convertToUserTimezone(pick.start_time, "full")}</div>
                      )}
                      <button 
                        className="aai-place-bet-btn"
                        onClick={() => openBetPlacementModal(pick)}
                      >
                        💰 Place Bet
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="aai-empty">No singles available for today.</div>
              )}
            </div>

            {/* Parlays */}
            <div className="aai-section">
              <div className="aai-section-header">
                <h2>Parlays</h2>
                <span className="aai-section-subtitle">Low-variance combinations</span>
              </div>
              {data?.parlays?.length ? (
                <div className="aai-grid">
                  {data.parlays.map((parlay, idx) => (
                    <div key={`parlay-${idx}`} className="aai-card">
                      <div className="aai-card-header">
                        <div className="aai-pick">{parlay.leg_count}-Leg Parlay</div>
                        <div className="aai-confidence-column">
                          <div className="aai-confidence-label">Form</div>
                          <div className="aai-confidence">{parlay.confidence}%</div>
                          {parlay.combined_confidence && parlay.combined_confidence !== parlay.confidence && (
                            <>
                              <div className="aai-confidence-label">Blended</div>
                              <div className="aai-confidence-combined">{parlay.combined_confidence}%</div>
                            </>
                          )}
                        </div>
                      </div>
                      <ul className="aai-legs">
                        {parlay.legs.map((leg, legIdx) => (
                          <li key={`${leg.game_id}-${legIdx}`}>
                            {leg.pick} <span>{leg.confidence}%</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="aai-empty">No parlays generated.</div>
              )}
            </div>
              {/* Custom Bet Builder */}
              <div className="aai-section">
                <div className="aai-section-header">
                  <h2>Custom Bet Builder</h2>
                  <span className="aai-section-subtitle">Build your own single or parlay from upcoming games</span>
                </div>
                <button className="aai-custom-builder-btn" onClick={openCustomBuilder}>
                  🎯 Build Custom Bet
                </button>
              </div>
          </>
        )}
      </div>
    </div>
    )}

      {/* Bet Placement Modal */}
      <BetPlacementModal 
        bet={selectedBet}
        isOpen={showPlacementModal}
        onClose={closeBetPlacementModal}
        onSuccess={handleBetPlacedSuccess}
      />

      {/* Custom Bet Builder Modal */}
      <ErrorBoundary>
        <CustomBetBuilder 
          games={data?.upcoming_games || []}
          isOpen={showCustomBuilder}
          onClose={closeCustomBuilder}
        />
      </ErrorBoundary>
    </div>
  );
}

export default AAIBetsPage;
