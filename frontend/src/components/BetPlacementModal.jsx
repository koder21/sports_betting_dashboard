import React, { useState } from "react";
import api from "../services/api.js";
import "../styles/BetPlacementModal.css";

function BetPlacementModal({ bet, isOpen, onClose, onSuccess }) {
  const [stake, setStake] = useState(50);
  const [odds, setOdds] = useState(bet?.odds || 2.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !bet) return null;

  const potentialWin = (stake * odds - stake).toFixed(2);

  const handlePlaceBet = async () => {
    try {
      setLoading(true);
      setError(null);

      const payload = {
        game_id: bet.game_id,
        pick: bet.pick,
        confidence: bet.confidence || 65,
        combined_confidence: bet.combined_confidence || bet.confidence || 65,
        stake: parseFloat(stake),
        odds: parseFloat(odds),
        reason: bet.reason || "AAI recommendation",
        sport: bet.sport || "NBA",
      };

      const response = await api.post("/bets/place-aai-single", payload);

      if (response.data.success) {
        onSuccess?.(response.data);
        onClose();
      } else {
        setError(response.data.error || "Failed to place bet");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Error placing bet");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bet-placement-overlay" onClick={onClose}>
      <div className="bet-placement-modal" onClick={(e) => e.stopPropagation()}>
        <div className="bet-placement-header">
          <h2>Place Bet</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="bet-placement-content">
          <div className="bet-details">
            <div className="detail-row">
              <span className="detail-label">Pick:</span>
              <span className="detail-value">{bet.pick}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Confidence:</span>
              <span className="detail-value">{bet.combined_confidence || bet.confidence || 65}%</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Matchup:</span>
              <span className="detail-value">{bet.away} @ {bet.home}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Reason:</span>
              <span className="detail-value">{bet.reason}</span>
            </div>
          </div>

          <div className="bet-inputs">
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
              <label>Odds</label>
              <input
                type="number"
                value={odds}
                onChange={(e) => setOdds(e.target.value)}
                min="1.01"
                step="0.05"
              />
            </div>
          </div>

          <div className="bet-calculation">
            <div className="calc-row">
              <span>Stake:</span>
              <span>${stake}</span>
            </div>
            <div className="calc-row">
              <span>Odds:</span>
              <span>{odds}x</span>
            </div>
            <div className="calc-row highlight">
              <span>Potential Win:</span>
              <span>${potentialWin}</span>
            </div>
          </div>

          {error && <div className="bet-error">{error}</div>}

          <div className="bet-actions">
            <button
              className="bet-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              className="bet-submit-btn"
              onClick={handlePlaceBet}
              disabled={loading}
            >
              {loading ? "Placing..." : "Place Bet"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BetPlacementModal;
