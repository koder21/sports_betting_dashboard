import React, { useState, useEffect } from "react";
import api from "../services/api.js";
import { getOddsFormat, calculateParlayOdds } from "../services/oddsService.js";
import "../styles/CustomBetBuilder.css";

function CustomBetBuilder({ games, isOpen, onClose }) {
  const [betType, setBetType] = useState("single"); // "single" or "parlay"
  const [selectedGames, setSelectedGames] = useState([]);
  const [stake, setStake] = useState(50);
  const [notes, setNotes] = useState("AAI Custom Bet");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [gameLegs, setGameLegs] = useState([]); // For parlay
  const [oddsFormat, setOddsFormat] = useState(getOddsFormat()); // Track odds format

  // Handle body overflow when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [isOpen]);

  // Listen for odds format changes
  useEffect(() => {
    const handleOddsFormatChange = (e) => {
      setOddsFormat(e.detail.format);
    };
    window.addEventListener('oddsFormatChanged', handleOddsFormatChange);
    return () => window.removeEventListener('oddsFormatChanged', handleOddsFormatChange);
  }, []);

  // Convert selected games to legs format
  useEffect(() => {
    const legs = selectedGames.map((game) => ({
      game_id: game.game_id,
      pick: game.selectedPick,
      odds: game.selectedOdds || 2.0,
      confidence: typeof game.selectedConfidence === "number" ? game.selectedConfidence : 0,
    }));
    setGameLegs(legs);
  }, [selectedGames]);

  // Early return AFTER all hooks
  if (!isOpen) return null;
  // Ensure games is an array
  const gamesList = Array.isArray(games) ? games : [];

  const getHomeTeamName = (game) => {
    const name = game.home_team_name || game.home || "Home";
    return `${name} ML`;
  };

  const getAwayTeamName = (game) => {
    const name = game.away_team_name || game.away || "Away";
    return `${name} ML`;
  };

  const toggleGameSelection = (game) => {
    setSelectedGames((prev) => {
      const exists = prev.find((g) => g.game_id === game.game_id);
      if (exists) {
        return prev.filter((g) => g.game_id !== game.game_id);
      }
      return [
        ...prev,
        { ...game, selectedPick: getHomeTeamName(game), selectedOdds: 2.0 },
      ];
    });
  };

  const updateGamePick = (gameId, pick, odds) => {
    setSelectedGames((prev) =>
      prev.map((g) =>
        g.game_id === gameId
          ? { ...g, selectedPick: pick, selectedOdds: parseFloat(odds) }
          : g
      )
    );
  };

  const handlePlaceBet = async () => {
    try {
      setLoading(true);
      setError(null);

      if (betType === "single") {
        if (selectedGames.length !== 1) {
          setError("Select exactly 1 game for a single bet");
          setLoading(false);
          return;
        }

        const game = selectedGames[0];
        const payload = {
          game_id: game.game_id,
          pick: game.selectedPick,
          stake: parseFloat(stake),
          odds: parseFloat(game.selectedOdds),
          notes: notes,
        };

        const response = await api.post("/bets/build-custom-single", payload);
        if (response.data.success) {
          onClose?.({ type: "single", ...response.data });
        } else {
          setError(response.data.error || "Failed to place bet");
        }
      } else {
        // Parlay
        if (selectedGames.length < 2) {
          setError("Select at least 2 games for a parlay");
          setLoading(false);
          return;
        }

        const payload = {
          legs: gameLegs.map(({ game_id, pick, odds, confidence }) => ({
            game_id,
            pick,
            odds: typeof odds === "number" ? odds : parseFloat(odds),
            confidence: typeof confidence === "number" ? confidence : 0,
          })),
          stake: parseFloat(stake),
          notes: notes,
        };

        const response = await api.post("/bets/build-custom-parlay", payload);
        if (response.data.success) {
          onClose?.({ type: "parlay", ...response.data });
        } else {
          setError(response.data.error || "Failed to build parlay");
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || "Error placing bet");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate parlay odds using utility (handles American/decimal)
  const parlayOdds = calculateParlayOdds(gameLegs.map(leg => leg.odds), 'decimal');
  const parlayProfit = (stake * (parlayOdds - 1)).toFixed(2);

  return (
    <div className="custom-bet-builder-overlay" onClick={onClose}>
      <div
        className="custom-bet-builder-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="builder-header">
          <h2>Build Custom Bet</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="builder-content">
          {/* Bet Type Selector */}
          <div className="bet-type-selector">
            <button
              className={`type-btn ${betType === "single" ? "active" : ""}`}
              onClick={() => setBetType("single")}
            >
              Single
            </button>
            <button
              className={`type-btn ${betType === "parlay" ? "active" : ""}`}
              onClick={() => setBetType("parlay")}
            >
              Parlay
            </button>
          </div>

          {/* Games List */}
          <div className="games-selection">
            <h3>Select Games {betType === "parlay" && `(${selectedGames.length})`}</h3>
            <div className="games-list">
              {Array.isArray(games) && games?.length ? (
                games.map((game) => {
                  const selected = selectedGames.some(
                    (g) => g.game_id === game.game_id
                  );
                  const selectedGame = selectedGames.find(
                    (g) => g.game_id === game.game_id
                  );

                  // Use home_team_name/away_team_name for clarity
                  const homeName = game.home_team_name || game.home || "Home";
                  const awayName = game.away_team_name || game.away || "Away";
                  // Try to use logo fields if present
                  const homeLogo = game.home_team_logo || game.home_logo || null;
                  const awayLogo = game.away_team_logo || game.away_logo || null;

                  return (
                    <div
                      key={game.game_id}
                      className={`game-card ${selected ? "selected" : ""}`}
                      onClick={() => toggleGameSelection(game)}
                    >
                      <div className="game-matchup">
                        <div className="team away">
                          {awayLogo && <img src={awayLogo} alt={awayName} className="team-logo" />}
                          <span>{awayName}</span>
                          <span className="team-label">(Away)</span>
                        </div>
                        <div className="at">@</div>
                        <div className="team home">
                          {homeLogo && <img src={homeLogo} alt={homeName} className="team-logo" />}
                          <span>{homeName}</span>
                          <span className="team-label">(Home)</span>
                        </div>
                      </div>
                      <div className="game-time">{game.start_time}</div>

                      {selected && (
                        <div
                          className="game-leg-editor"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="leg-input">
                            <label>Pick</label>
                            <select
                              value={selectedGame?.selectedPick || homeName + ' ML'}
                              onChange={(e) =>
                                updateGamePick(
                                  game.game_id,
                                  e.target.value,
                                  selectedGame?.selectedOdds || 2.0
                                )
                              }
                            >
                              <option value={homeName + ' ML'}>{homeName} (Home)</option>
                              <option value={awayName + ' ML'}>{awayName} (Away)</option>
                              <option value="Over">Over Total</option>
                              <option value="Under">Under Total</option>
                            </select>
                          </div>

                          <div className="leg-input">
                            <label>Odds</label>
                            <input
                              type="number"
                              value={selectedGame?.selectedOdds || 2.0}
                              onChange={(e) =>
                                updateGamePick(
                                  game.game_id,
                                  selectedGame?.selectedPick || getHomeTeamName(game),
                                  e.target.value
                                )
                              }
                              min="1.01"
                              step="0.05"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="no-games">No games available</div>
              )}
            </div>
          </div>

          {/* Stake and Notes */}
          <div className="builder-inputs">
            <div className="input-group">
              <label>Stake ($)</label>
              <input
                type="number"
                value={stake}
                onChange={(e) => setStake(e.target.value)}
                min="1"
                step="10"
              />
            </div>

            <div className="input-group">
              <label>Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional notes about this bet..."
              />
            </div>
          </div>

          {/* Calculation Summary */}
          {betType === "parlay" && selectedGames.length >= 2 && (
            <div className="parlay-summary">
              <div className="summary-row">
                <span>Legs:</span>
                <span>{selectedGames.length}</span>
              </div>
              <div className="summary-row">
                <span>Parlay Odds:</span>
                <span>{parlayOdds.toFixed(3)}x</span>
              </div>
              <div className="summary-row highlight">
                <span>Potential Profit:</span>
                <span>${parlayProfit}</span>
              </div>
            </div>
          )}

          {error && <div className="builder-error">{error}</div>}

          <div className="builder-actions">
            <button
              className="builder-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              className="builder-submit-btn"
              onClick={handlePlaceBet}
              disabled={
                loading ||
                (betType === "single" && selectedGames.length !== 1) ||
                (betType === "parlay" && selectedGames.length < 2)
              }
            >
              {loading ? "Building..." : "Build & Place Bet"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CustomBetBuilder;
