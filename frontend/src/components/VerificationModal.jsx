import React, { useState, useEffect } from 'react';
import './VerificationModal.css';

const VerificationModal = React.memo(({ results, onClose, onApply }) => {
  const [selectedCorrections, setSelectedCorrections] = useState([]);

  useEffect(() => {
    if (results && results.discrepancies) {
      // Pre-select all discrepancies
      setSelectedCorrections(results.discrepancies.map((_, idx) => idx));
    }
  }, [results]);

  if (!results || !results.discrepancies) return null;

  const toggleCorrection = (idx) => {
    setSelectedCorrections((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    );
  };

  const handleApply = () => {
    const correctionsToApply = selectedCorrections.map((idx) => results.discrepancies[idx]);
    onApply(correctionsToApply);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content verification-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚠️ Bet Verification Results</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close modal">×</button>
        </div>

        <div className="modal-body">
          <div className="verification-summary">
            <p><strong>Total Graded Bets:</strong> {results.total_graded}</p>
            <p><strong>Discrepancies Found:</strong> {results.discrepancies_found}</p>
          </div>

          {results.discrepancies.length === 0 ? (
            <div className="no-discrepancies">
              <p>✓ All bets are correct!</p>
            </div>
          ) : (
            <div className="discrepancies-list">
              <p className="warning-text">
                ⚠️ Please manually verify each discrepancy before applying corrections:
              </p>

              {results.discrepancies.map((disc, idx) => (
                <div key={idx} className="discrepancy-item">
                  <label className="discrepancy-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedCorrections.includes(idx)}
                      onChange={() => toggleCorrection(idx)}
                      aria-label={`Select correction ${idx + 1}`}
                    />
                    <div className="discrepancy-details">
                      {disc.type === "parlay" ? (
                        <>
                          <div className="disc-header">
                            <strong>Parlay</strong> ({disc.legs?.length || 0} legs)
                            <span className={`status-badge ${disc.expected_status}`}>
                              {disc.current_status} → {disc.expected_status}
                            </span>
                          </div>
                          <div className="disc-info">
                            <div>Stake: ${disc.original_stake?.toFixed(2) || 0}</div>
                            <div>Odds: {disc.parlay_odds > 0 ? '+' : ''}{disc.parlay_odds?.toFixed(0) || 0}</div>
                          </div>
                          {disc.leg_discrepancies && disc.leg_discrepancies.length > 0 && (
                            <div className="leg-discrepancies">
                              <strong>Leg Issues:</strong>
                              {disc.leg_discrepancies.map((leg, lidx) => (
                                <div key={lidx} className="leg-disc">
                                  • {leg.selection}: {leg.current_status} → {leg.expected_status}
                                  <br />
                                  <small>{leg.reason}</small>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          <div className="disc-header">
                            <strong>Single Bet:</strong> {disc.selection}
                            <span className={`status-badge ${disc.expected_status}`}>
                              {disc.current_status} → {disc.expected_status}
                            </span>
                          </div>
                          <div className="disc-info">
                            <div>Stake: ${disc.stake?.toFixed(2) || 0}</div>
                            <div>Odds: {disc.odds > 0 ? '+' : ''}{disc.odds?.toFixed(0) || 0}</div>
                          </div>
                          {disc.reason && (
                            <div className="disc-reason">
                              <strong>Reason:</strong> {disc.reason}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </label>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleApply}
            disabled={selectedCorrections.length === 0}
          >
            Apply {selectedCorrections.length} Correction{selectedCorrections.length !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </div>
  );
});

VerificationModal.displayName = 'VerificationModal';

export default VerificationModal;
