import React, { useState, useEffect, useMemo } from "react";
import api from "../services/api.js";
import "./BetsPage.css";

function BetsPage() {
  const [rawText, setRawText] = useState("");
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copyingAI, setCopyingAI] = useState(false);
  const [error, setError] = useState(null);
  const [groupedBets, setGroupedBets] = useState({});
  const [activeTab, setActiveTab] = useState("pending");
  const [showWins, setShowWins] = useState(true);
  const [showLosses, setShowLosses] = useState(true);
  const [dateFilter, setDateFilter] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verificationResults, setVerificationResults] = useState(null);
  const [showVerificationModal, setShowVerificationModal] = useState(false);

  useEffect(() => {
    fetchBets();
  }, []);

  const fetchBets = async () => {
    setLoading(true);
    try {
      const response = await api.get("/bets/all");
      if (response.data.bets) {
        setBets(response.data.bets);
        groupBets(response.data.bets);
      }
    } catch (err) {
      setError("Failed to fetch bets");
      console.error(err);
    }
    setLoading(false);
  };

  const groupBets = (betList) => {
    const grouped = {};
    betList.forEach((bet) => {
      const groupId = bet.parlay_id || `single-${bet.id}`;
      if (!grouped[groupId]) {
        grouped[groupId] = [];
      }
      grouped[groupId].push(bet);
    });
    setGroupedBets(grouped);
  };

  const toPST = (dateString) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      // Convert to PST (UTC-8) or PDT (UTC-7)
      return new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/Los_Angeles',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).format(date);
    } catch {
      return null;
    }
  };

  const filteredGroupedBets = useMemo(() => {
    // Filter by tab
    let filtered = Object.entries(groupedBets).filter(([groupId, groupBets]) => {
      const allWon = groupBets.every(b => b.status === "won");
      const anyLost = groupBets.some(b => b.status === "lost");
      const allPending = groupBets.every(b => b.status === "pending");
      const anyPending = groupBets.some(b => b.status === "pending");
      const allVoided = groupBets.every(b => b.status === "void");

      if (activeTab === "finished") {
        return (allWon || anyLost) && !anyPending && !allVoided;
      } else if (activeTab === "pending") {
        return anyPending && !allVoided;
      } else if (activeTab === "voided") {
        return allVoided;
      }
      return true;
    });

    // Filter by win/loss (only applies to finished bets)
    if (activeTab === "finished") {
      filtered = filtered.filter(([groupId, groupBets]) => {
        const allWon = groupBets.every(b => b.status === "won");
        const anyLost = groupBets.some(b => b.status === "lost");
        
        if (!showWins && allWon) return false;
        if (!showLosses && anyLost) return false;
        return true;
      });
    }

    // Filter by date
    if (dateFilter) {
      filtered = filtered.filter(([groupId, groupBets]) => {
        return groupBets.some(bet => {
          if (bet.game?.scheduled_at) {
            const pstDate = toPST(bet.game.scheduled_at);
            const filterDate = new Date(dateFilter).toLocaleDateString('en-US', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit'
            });
            return pstDate === filterDate;
          }
          return false;
        });
      });
    }

    return Object.fromEntries(filtered);
  }, [groupedBets, activeTab, showWins, showLosses, dateFilter]);

  const copyForAI = async () => {
    setCopyingAI(true);
    setError(null);

    try {
      const response = await api.get("/games/ai-context");
      
      if (response.data.text) {
        await navigator.clipboard.writeText(response.data.text);
        
        // Show success message
        const originalError = error;
        setError(`✓ Copied ${response.data.yesterday_count} yesterday's results and ${response.data.today_count} today's games!`);
        setTimeout(() => {
          setError(originalError);
        }, 3000);
      }
    } catch (err) {
      setError("Failed to copy AI context: " + (err.response?.data?.detail || err.message));
      console.error(err);
    }
    
    setCopyingAI(false);
  };

  const verifyBets = async () => {
    setVerifying(true);
    setError(null);

    try {
      const response = await api.post("/bets/verify");
      setVerificationResults(response.data);
      
      if (response.data.discrepancies_found > 0) {
        setShowVerificationModal(true);
      } else {
        setError("✓ All bets verified correctly! No discrepancies found.");
        setTimeout(() => setError(null), 5000);
      }
    } catch (err) {
      setError("Failed to verify bets: " + (err.response?.data?.detail || err.message));
      console.error(err);
    }

    setVerifying(false);
  };

  const applyCorrections = async (corrections) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/bets/apply-corrections", corrections);
      
      setShowVerificationModal(false);
      setVerificationResults(null);
      
      // Refresh bets
      await fetchBets();
      
      setError(`✓ Applied ${response.data.corrected} corrections successfully!`);
      setTimeout(() => setError(null), 5000);
    } catch (err) {
      setError("Failed to apply corrections: " + (err.response?.data?.detail || err.message));
      console.error(err);
    }

    setLoading(false);
  };

  const placeBets = async () => {
    if (!rawText.trim()) {
      setError("Please enter bet details");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post("/bets/place-multiple", null, {
        params: { raw_text: rawText },
      });

      if (response.data.status === "ok") {
        setRawText("");
        fetchBets();
      } else {
        let errorMsg = response.data.message || "Failed to place bets";
        
        // Show detailed error for invalid bets
        if (response.data.invalid_bets && response.data.invalid_bets.length > 0) {
          const invalidList = response.data.invalid_bets
            .map(b => `• ${b.selection}: ${b.reason}`)
            .join("\n");
          errorMsg = errorMsg + "\n\n" + invalidList;
        }
        
        setError(errorMsg);
      }
    } catch (err) {
      setError("Error placing bets: " + (err.response?.data?.message || err.message));
      console.error(err);
    }
    setLoading(false);
  };

  const getBetStats = () => {
    const total = bets.length;
    const won = bets.filter((b) => b.status === "won").length;
    const lost = bets.filter((b) => b.status === "lost").length;
    const pending = bets.filter((b) => b.status === "pending").length;
    
    // Calculate total staked using original_stake to avoid counting parlay legs multiple times
    const seenParlays = new Set();
    let totalStaked = 0;
    let totalProfit = 0;
    
    bets.forEach((b) => {
      if (b.parlay_id) {
        // For parlays, only count once per parlay
        if (!seenParlays.has(b.parlay_id)) {
          const parlayStake = b.original_stake || b.stake || 0;
          totalStaked += parlayStake;
          seenParlays.add(b.parlay_id);
          
          // Calculate parlay profit based on parlay status
          const parlayBets = bets.filter(bet => bet.parlay_id === b.parlay_id);
          const allWon = parlayBets.every(bet => bet.status === "won");
          const anyLost = parlayBets.some(bet => bet.status === "lost");
          
          if (allWon) {
            // Parlay won - calculate profit using parlay odds
            const parlayOdds = b.parlay_odds || 0;
            if (parlayOdds > 0) {
              totalProfit += parlayStake * (parlayOdds / 100);
            } else if (parlayOdds < 0) {
              totalProfit += parlayStake / (Math.abs(parlayOdds) / 100);
            }
          } else if (anyLost) {
            // Parlay lost - lose the stake
            totalProfit -= parlayStake;
          }
          // If pending, don't add to profit
        }
      } else {
        // For singles, calculate profit based on status
        const singleStake = b.original_stake || b.stake || 0;
        totalStaked += singleStake;
        
        if (b.status === "won") {
          const odds = b.odds || 0;
          if (odds > 0) {
            totalProfit += singleStake * (odds / 100);
          } else if (odds < 0) {
            totalProfit += singleStake / (Math.abs(odds) / 100);
          }
        } else if (b.status === "lost") {
          totalProfit -= singleStake;
        }
        // If pending or other status, don't add to profit
      }
    });

    // Protect against NaN or Infinity
    if (!isFinite(totalProfit)) totalProfit = 0;
    if (!isFinite(totalStaked)) totalStaked = 0;

    return { total, won, lost, pending, totalStaked, totalProfit };
  };

  const stats = getBetStats();
  const winPercentage = stats.total > 0 ? ((stats.won / stats.total) * 100).toFixed(1) : 0;

  return (
    <div className="bets-page">
      <h1>Betting Tracker</h1>

      {/* Stats Overview */}
      <div className="stats-container">
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total Bets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#4CAF50" }}>
            {stats.won}
          </div>
          <div className="stat-label">Won</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#f44336" }}>
            {stats.lost}
          </div>
          <div className="stat-label">Lost</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#FF9800" }}>
            {stats.pending}
          </div>
          <div className="stat-label">Pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{winPercentage}%</div>
          <div className="stat-label">Win Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">${Math.round(stats.totalStaked)}</div>
          <div className="stat-label">Total Staked</div>
        </div>
        <div className="stat-card">
          <div
            className="stat-value"
            style={{ color: stats.totalProfit >= 0 ? "#4CAF50" : "#f44336" }}
          >
            {stats.totalProfit > 0 ? '+' : ''}${Math.round(stats.totalProfit)}
          </div>
          <div className="stat-label">Total Profit/Loss</div>
        </div>
      </div>

      {/* Input Section */}
      <div className="input-section">
        <h2>Place New Bets</h2>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder={`Parlay #1 (2 legs)
Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-07, Odds: -150, Stake: 300, Reason: Strong matchup.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-07, Odds: -110, Stake: 300, Reason: High usage.`}
          rows={8}
          className="bet-textarea"
        />
        <div className="button-group">
          <button
            onClick={placeBets}
            disabled={loading || !rawText.trim()}
            className="btn btn-primary"
          >
            {loading ? "Processing..." : "Place Bets"}
          </button>
          <button
            onClick={copyForAI}
            disabled={copyingAI}
            className="btn btn-secondary"
            style={{ marginLeft: 'auto' }}
          >
            {copyingAI ? "Copying..." : "Copy for AI"}
          </button>
          <button
            onClick={verifyBets}
            disabled={verifying || loading}
            className="btn btn-warning"
          >
            {verifying ? "Verifying..." : "Re-check Bets"}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Bets List */}
      <div className="bets-list">
        <div className="bets-header">
          <h2>Your Bets</h2>
          
          {/* Tabs */}
          <div className="tabs">
            <button
              className={activeTab === "finished" ? "tab active" : "tab"}
              onClick={() => setActiveTab("finished")}
            >
              Finished
            </button>
            <button
              className={activeTab === "pending" ? "tab active" : "tab"}
              onClick={() => setActiveTab("pending")}
            >
              Pending
            </button>
            <button
              className={activeTab === "voided" ? "tab active" : "tab"}
              onClick={() => setActiveTab("voided")}
            >
              Voided
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="filters">
          {activeTab === "finished" && (
            <div className="filter-group">
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={showWins}
                  onChange={(e) => setShowWins(e.target.checked)}
                />
                <span>Show Wins</span>
              </label>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={showLosses}
                  onChange={(e) => setShowLosses(e.target.checked)}
                />
                <span>Show Losses</span>
              </label>
            </div>
          )}
          <div className="filter-group">
            <label>
              <span>Filter by Date (PST):</span>
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="date-filter"
              />
              {dateFilter && (
                <button
                  onClick={() => setDateFilter("")}
                  className="clear-date"
                  title="Clear date filter"
                >
                  ✕
                </button>
              )}
            </label>
          </div>
        </div>

        {loading && <div className="loading">Loading...</div>}
        {Object.entries(filteredGroupedBets).map(([groupId, groupBets]) => (
          <BetGroup key={groupId} bets={groupBets} />
        ))}
        {Object.keys(filteredGroupedBets).length === 0 && !loading && (
          <div className="no-bets">
            {bets.length === 0
              ? "No bets yet. Place some bets to get started!"
              : `No ${activeTab} bets match your filters.`}
          </div>
        )}
      </div>

      {showVerificationModal && (
        <VerificationModal
          results={verificationResults}
          onClose={() => setShowVerificationModal(false)}
          onApply={applyCorrections}
        />
      )}
    </div>
  );
}

function BetGroup({ bets }) {
  const isParlay = bets.length > 1;
  const parlayName = bets[0]?.parlay_id?.substring(0, 8) || `Single #${bets[0]?.id}`;
  // For parlays, use original_stake from any bet in the group (they're all the same parlay)
  // For singles, use the bet's original_stake
  const totalStake = isParlay
    ? (bets[0]?.original_stake || bets[0]?.stake || 0)
    : bets.reduce((sum, b) => sum + (b.original_stake || b.stake || 0), 0);
  const parlay_odds = bets[0]?.parlay_odds || bets[0]?.odds || 0; // Use parlay odds if available
  const allWon = bets.every((b) => b.status === "won");
  const anyLost = bets.some((b) => b.status === "lost");
  const allPending = bets.every((b) => b.status === "pending");

  let groupStatus = allPending ? "pending" : anyLost ? "lost" : allWon ? "won" : "pending";
  const statusColor =
    groupStatus === "won" ? "#4CAF50" : groupStatus === "lost" ? "#f44336" : "#FF9800";

  let totalProfit = 0;
  if (isParlay) {
    if (groupStatus === "won") {
      if (parlay_odds > 0) {
        totalProfit = totalStake * (parlay_odds / 100);
      } else if (parlay_odds < 0) {
        totalProfit = totalStake / (Math.abs(parlay_odds) / 100);
      }
    } else if (groupStatus === "lost") {
      totalProfit = -totalStake;
    }
  } else {
    // For singles, calculate profit based on status and odds
    bets.forEach((b) => {
      if (b.status === "won") {
        const stake = b.original_stake || b.stake || 0;
        const odds = b.odds || 0;
        if (odds > 0) {
          totalProfit += stake * (odds / 100);
        } else if (odds < 0) {
          totalProfit += stake / (Math.abs(odds) / 100);
        }
      } else if (b.status === "lost") {
        const stake = b.original_stake || b.stake || 0;
        totalProfit -= stake;
      }
    });
  }

  // Protect against NaN or Infinity
  if (!isFinite(totalProfit)) totalProfit = 0;

  return (
    <div className="bet-group">
      <div className="group-header" style={{ borderLeftColor: statusColor }}>
        <div className="group-title">
          <span className="group-label">{isParlay ? `Parlay (${bets.length} legs)` : "Single"}</span>
          <span className="group-status" style={{ color: statusColor }}>
            {groupStatus.toUpperCase()}
          </span>
        </div>
        <div className="group-summary">
          <span>Stake: ${Math.round(totalStake)}</span>
          <span>Odds: {parlay_odds > 0 ? '+' : ''}{Math.round(parlay_odds)}</span>
          {totalProfit !== 0 && (
            <span style={{ color: totalProfit > 0 ? "#4CAF50" : "#f44336" }}>
              P&L: {totalProfit > 0 ? '+' : ''}${Math.round(totalProfit)}
            </span>
          )}
        </div>
      </div>

      <div className="bets-in-group">
        {bets.map((bet) => (
          <BetCard key={bet.id} bet={bet} />
        ))}
      </div>
    </div>
  );
}

function BetCard({ bet }) {
  const statusColor =
    bet.status === "won" ? "#4CAF50" : bet.status === "lost" ? "#f44336" : "#FF9800";

  // Extract stat type from selection for prop bets
  const getStatLabel = () => {
    if (bet.bet_type !== "prop" || !bet.selection) return "";
    
    // Try to extract stat type from selection (e.g., "over 27.5 pts" -> "pts")
    const match = bet.selection.match(/(?:over|under)\s+[\d.]+\s+(\w+)/i);
    if (match) {
      return match[1]; // Returns "pts", "ast", "reb", etc.
    }
    
    // Fallback to market field if available
    if (bet.market) {
      return bet.market;
    }
    
    return "";
  };

  const statLabel = getStatLabel();

  return (
    <div className="bet-card">
      <div className="bet-header">
        <div className="bet-selection">{bet.selection}</div>
        <div className="bet-status" style={{ color: statusColor }}>
          {bet.status.toUpperCase()}
        </div>
      </div>

      <div className="bet-details">
        {bet.game && (
          <div className="bet-detail-section">
            <strong>Game:</strong> {bet.game.away_team} @ {bet.game.home_team}
            {bet.game.status !== "scheduled" && (
              <span className="score">
                {bet.game.away_score} - {bet.game.home_score}
              </span>
            )}
            <span className="date">{formatDate(bet.game.scheduled_at)}</span>
            <div className="detail-item" style={{ marginTop: "0.5rem" }}>
              <span>Game ID:</span> <strong style={{ fontFamily: "monospace" }}>{bet.game.game_id}</strong>
            </div>
          </div>
        )}
        {!bet.game && bet.player && (
          <div className="detail-item" style={{ marginTop: "0.5rem" }}>
            <span>Game ID:</span> <strong style={{ fontFamily: "monospace" }}>{bet.game_id || "N/A"}</strong>
          </div>
        )}

        {bet.player && (
          <div className="bet-detail-section">
            <strong>Player:</strong> {bet.player.name} ({bet.player.team})
          </div>
        )}

        {bet.player_name && !bet.player && (
          <div className="bet-detail-section">
            <strong>Player:</strong> {bet.player_name}
          </div>
        )}

        <div className="bet-detail-section">
          <div className="detail-item">
            <span>Type:</span> <strong>{bet.bet_type}</strong>
          </div>
          <div className="detail-item">
            <span>Odds:</span> <strong>{bet.odds > 0 ? '+' : ''}{Math.round(bet.odds)}</strong>
          </div>
          <div className="detail-item">
            <span>Stake:</span> <strong>${Math.round(bet.stake)}</strong>
          </div>
          {bet.result_value !== null && bet.result_value !== undefined && (
            <div className="detail-item">
              <span>Result:</span>{" "}
              <strong style={{ color: bet.status === "won" ? "#4CAF50" : bet.status === "lost" ? "#f44336" : "#FF9800" }}>
                {bet.result_value}{statLabel ? ` ${statLabel}` : ""}
              </strong>
            </div>
          )}
          {bet.profit !== null && bet.profit !== undefined && (
            <div className="detail-item">
              <span>Profit:</span>{" "}
              <strong style={{ color: bet.profit > 0 ? "#4CAF50" : "#f44336" }}>
                {bet.profit > 0 ? '+' : ''}${Math.round(bet.profit)}
              </strong>
            </div>
          )}
        </div>

        {bet.reason && (
          <div className="bet-reason">
            <em>{bet.reason}</em>
          </div>
        )}
      </div>
    </div>
  );
}

function formatDate(dateString) {
  if (!dateString) return "";
  try {
    const date = new Date(dateString);
    // Display in PST timezone
    return date.toLocaleDateString("en-US", {
      timeZone: "America/Los_Angeles",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
}

function VerificationModal({ results, onClose, onApply }) {
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
          <button className="modal-close" onClick={onClose}>×</button>
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
}

export default BetsPage;