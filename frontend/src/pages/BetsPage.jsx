import React, { useState, useEffect, useMemo } from "react";
import api from "../services/api.js";
import { convertToUserTimezone } from "../services/timezoneService.js";
import { getOddsFormat, formatOdds } from "../services/oddsService.js";
import "./BetsPage.css";

const calcAmericanProfit = (stake, odds) => {
  if (!odds || stake === 0) return 0;
  if (odds > 0) return stake * (odds / 100);
  return stake / (Math.abs(odds) / 100);
};

const calcDecimalProfit = (stake, decimalOdds) => {
  if (!decimalOdds || stake === 0) return 0;
  return stake * (decimalOdds - 1);
};

const calcParlayProfit = (stake, parlayOdds) => {
  if (!parlayOdds || stake === 0) return 0;
  // Heuristic: treat large magnitude or negative values as American odds
  if (parlayOdds <= 0 || Math.abs(parlayOdds) >= 100) {
    return calcAmericanProfit(stake, parlayOdds);
  }
  // Otherwise treat as decimal odds
  return calcDecimalProfit(stake, parlayOdds);
};

const getGroupStatus = (bets) => {
  const anyVoided = bets.some((b) => b.status === "void");
  if (anyVoided) return "void";
  const allPending = bets.every((b) => b.status === "pending");
  if (allPending) return "pending";
  const anyLost = bets.some((b) => b.status === "lost");
  if (anyLost) return "lost";
  const allWon = bets.every((b) => b.status === "won");
  if (allWon) return "won";
  return "pending";
};

const computeGroupPnlAndStake = (groupBets) => {
  const isParlay = groupBets.length > 1 && groupBets[0].parlay_id;
  const status = getGroupStatus(groupBets);
  let stake = 0;
  let pnl = 0;

  if (status === "void") {
    return { stake: 0, pnl: 0 };
  }

  if (isParlay) {
    stake = groupBets[0].original_stake || groupBets.reduce((sum, b) => sum + (b.stake || 0), 0) || 0;
    if (status === "won") {
      pnl = calcParlayProfit(stake, groupBets[0].parlay_odds || 0);
    } else if (status === "lost") {
      pnl = -stake;
    }
  } else {
    groupBets.forEach((b) => {
      const s = b.original_stake || b.stake || 0;
      stake += s;
      if (b.status === "won") {
        pnl += calcAmericanProfit(s, b.odds || 0);
      } else if (b.status === "lost") {
        pnl -= s;
      }
    });
  }

  if (!isFinite(pnl)) pnl = 0;
  if (!isFinite(stake)) stake = 0;
  return { stake, pnl };
};

function BetsPage() {
  const [rawText, setRawText] = useState("");
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copyingAI, setCopyingAI] = useState(false);
  const [oddsFormat, setOddsFormat] = useState(getOddsFormat());
  const [error, setError] = useState(null);
  const [groupedBets, setGroupedBets] = useState({});
  const [activeTab, setActiveTab] = useState("pending");
  const [showWins, setShowWins] = useState(true);
  const [showLosses, setShowLosses] = useState(true);
  const [dateFilter, setDateFilter] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verificationResults, setVerificationResults] = useState(null);
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [collapsedDays, setCollapsedDays] = useState({});
  const [expandedBets, setExpandedBets] = useState({});
  const [aiContextData, setAiContextData] = useState(null);
  const [showCopyRetry, setShowCopyRetry] = useState(false);

  useEffect(() => {
    fetchBets();
  }, []);

  useEffect(() => {
    const handleOddsFormatChange = (e) => {
      setOddsFormat(e.detail.format);
    };
    window.addEventListener('oddsFormatChanged', handleOddsFormatChange);
    return () => window.removeEventListener('oddsFormatChanged', handleOddsFormatChange);
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
      // For date filtering, we need the date in user's timezone
      return convertToUserTimezone(dateString, "date");
    } catch {
      return null;
    }
  };

  const getDateLabel = (dateStr) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const dateObj = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const todayObj = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const yesterdayObj = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());

    if (dateObj.getTime() === todayObj.getTime()) {
      return "Today";
    } else if (dateObj.getTime() === yesterdayObj.getTime()) {
      return "Yesterday";
    } else {
      return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }
  };

  const filteredGroupedBets = useMemo(() => {
    // Filter by tab
    let filtered = Object.entries(groupedBets).filter(([groupId, groupBets]) => {
      const allWon = groupBets.every(b => b.status === "won");
      const anyLost = groupBets.some(b => b.status === "lost");
      const allPending = groupBets.every(b => b.status === "pending");
      const anyPending = groupBets.some(b => b.status === "pending");
      const anyVoided = groupBets.some(b => b.status === "void");
      const allVoided = groupBets.every(b => b.status === "void");

      if (activeTab === "finished") {
        return (allWon || anyLost) && !anyPending && !anyVoided;
      } else if (activeTab === "pending") {
        return anyPending && !anyVoided;
      } else if (activeTab === "voided") {
        return anyVoided || allVoided;
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

  const betsByDay = useMemo(() => {
    const dayMap = {};
    Object.entries(filteredGroupedBets).forEach(([groupId, groupBets]) => {
      if (groupBets.length === 0) return;
      if (activeTab !== "voided" && groupBets.some(b => b.status === "void")) return;
      const placedDate = groupBets[0].placed_at;
      if (!placedDate) return;
      
      const dateStr = formatDate(placedDate);
      if (!dayMap[dateStr]) {
        dayMap[dateStr] = { bets: [], pnl: 0, totalStake: 0 };
      }
      dayMap[dateStr].bets.push([groupId, groupBets]);
      
      // Calculate total stake for the day
      const isParlay = groupBets.length > 1 && groupBets[0].parlay_id;
      const stake = isParlay
        ? (groupBets[0].original_stake || (groupBets[0].stake * groupBets.length) || 0)
        : (groupBets[0].original_stake || groupBets[0].stake || 0);
      dayMap[dateStr].totalStake += stake;
      
      // Calculate P&L for this group (either parlay or single/multiple singles)
      let groupPnl = 0;
      
      if (isParlay) {
        // For parlay: use original stake, or fallback to leg stake * legs
        const status = getGroupStatus(groupBets);
        
        if (status === "won") {
          groupPnl = calcParlayProfit(stake, groupBets[0].parlay_odds || 0);
        } else if (status === "lost") {
          groupPnl = -stake;
        } else {
          groupPnl = 0;
        }
      } else {
        // For singles: sum profit from each bet
        groupBets.forEach((b) => {
          const betStake = b.original_stake || b.stake || 0;
          if (b.status === "won") {
            groupPnl += calcAmericanProfit(betStake, b.odds || 0);
          } else if (b.status === "lost") {
            groupPnl -= betStake;
          }
        });
      }
      
      if (!isFinite(groupPnl)) groupPnl = 0;
      dayMap[dateStr].pnl += groupPnl;
    });

    // Sort days in descending order (most recent first)
    const sortedDays = Object.entries(dayMap).sort(([dateA], [dateB]) => {
      return new Date(dateB) - new Date(dateA);
    });

    return sortedDays.map(([dateStr, dayData]) => ([dateStr, dayData.bets, dayData.pnl, dayData.totalStake]));
  }, [filteredGroupedBets]);

  // Auto-initialize collapsed state when betsByDay changes
  useEffect(() => {
    const newCollapsedState = {};
    betsByDay.forEach(([dateStr]) => {
      const isToday = getDateLabel(dateStr) === "Today";
      const isYesterday = getDateLabel(dateStr) === "Yesterday";
      
      if (activeTab === "pending") {
        // Collapse all except today
        newCollapsedState[dateStr] = !isToday;
      } else if (activeTab === "finished") {
        // Collapse all except yesterday
        newCollapsedState[dateStr] = !isYesterday;
      } else {
        // voided: collapse all
        newCollapsedState[dateStr] = true;
      }
    });
    setCollapsedDays(newCollapsedState);
  }, [betsByDay, activeTab]);

  const copyForAI = async () => {
    setCopyingAI(true);
    setError(null);
    setShowCopyRetry(false);

    try {
      // Use the fresh endpoint to scrape latest data before copying
      setError("🔄 Fetching fresh data (games, results, injuries)...");
      const response = await api.get("/games/ai-context-fresh");
      
      if (response.data.text) {
        // Store the data for retry if clipboard fails
        setAiContextData(response.data);
        
        try {
          await navigator.clipboard.writeText(response.data.text);
          
          // Show success message
          setError(`✓ Copied ${response.data.yesterday_count} yesterday's results and ${response.data.today_count} upcoming games with fresh data!`);
          setTimeout(() => {
            setError(null);
          }, 3000);
        } catch (clipboardErr) {
          // Check if it's the "Document is not focused" error
          if (clipboardErr.message.includes("Document is not focused")) {
            setError("⚠️ Failed to copy: Browser tab is not focused. Please click on the webpage and try again.");
            setShowCopyRetry(true);
          } else {
            setError("Failed to copy to clipboard: " + clipboardErr.message);
          }
        }
      }
    } catch (err) {
      setError("Failed to fetch AI context: " + (err.response?.data?.detail || err.message));
      console.error(err);
    }
    
    setCopyingAI(false);
  };

  const retryClipboardCopy = async () => {
    if (!aiContextData) {
      setError("No data to copy. Please fetch again.");
      return;
    }
    
    setCopyingAI(true);
    setError(null);

    try {
      await navigator.clipboard.writeText(aiContextData.text);
      
      // Show success message
      setError(`✓ Copied ${aiContextData.yesterday_count} yesterday's results and ${aiContextData.today_count} upcoming games!`);
      setShowCopyRetry(false);
      setTimeout(() => {
        setError(null);
      }, 3000);
    } catch (err) {
      setError("Failed to copy to clipboard: " + err.message);
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

  const deletePendingBet = async (betId) => {
    if (!window.confirm("Are you sure you want to delete this pending bet?")) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.delete(`/bets/pending/${betId}`);
      
      if (response.data.status === "ok") {
        setError(`✓ Bet deleted successfully`);
        setTimeout(() => setError(null), 3000);
        await fetchBets();
      } else {
        setError(response.data.message || "Failed to delete bet");
      }
    } catch (err) {
      setError("Error deleting bet: " + (err.response?.data?.message || err.message));
      console.error(err);
    }
    
    setLoading(false);
  };

  const deleteAllPendingBets = async () => {
    if (!window.confirm("Are you sure you want to delete ALL pending bets? This cannot be undone.")) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.delete("/bets/pending-all");
      
      if (response.data.status === "ok") {
        const deletedCount = response.data.deleted || 0;
        setError(`✓ ${deletedCount} pending bet${deletedCount !== 1 ? 's' : ''} deleted successfully`);
        setTimeout(() => setError(null), 3000);
        await fetchBets();
      } else {
        setError(response.data.message || "Failed to delete pending bets");
      }
    } catch (err) {
      setError("Error deleting pending bets: " + (err.response?.data?.message || err.message));
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
    // Count unique bets (groups/parlays), not individual legs, excluding voided
    let uniqueBets = 0;
    
    // Count outcomes per bet group
    let won = 0;
    let lost = 0;
    let pending = 0;
    
    // Count individual legs
    let legsWon = 0;
    let legsLost = 0;
    
    Object.entries(groupedBets).forEach(([_, groupBets]) => {
      // Skip voided bets
      if (groupBets.some(b => b.status === "void")) return;
      
      uniqueBets++;
      const status = getGroupStatus(groupBets);
      if (status === "won") won++;
      else if (status === "lost") lost++;
      else if (status === "pending") pending++;
      
      // Count individual legs (track won/lost; pending is tracked separately in display)
      groupBets.forEach(leg => {
        if (leg.status === "won") legsWon++;
        else if (leg.status === "lost") legsLost++;
      });
    });
    
    // Calculate totals from all groups (global total, independent of tab)
    let totalStaked = 0;
    let totalProfit = 0;
    Object.entries(groupedBets).forEach(([_, groupBets]) => {
      if (groupBets.some(b => b.status === "void")) return;
      const { stake, pnl } = computeGroupPnlAndStake(groupBets);
      totalStaked += stake;
      totalProfit += pnl;
    });

    // Protect against NaN or Infinity
    if (!isFinite(totalProfit)) totalProfit = 0;
    if (!isFinite(totalStaked)) totalStaked = 0;

    return { total: uniqueBets, won, lost, pending, legsWon, legsLost, totalStaked, totalProfit };
  };

  const stats = getBetStats();
  const totalWins = stats.legsWon + stats.won;
  const totalOutcomes = stats.legsWon + stats.legsLost + stats.won + stats.lost;
  const winPercentage = totalOutcomes > 0 ? ((totalWins / totalOutcomes) * 100).toFixed(1) : 0;

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
          <div className="stat-value">{stats.legsWon}W - {stats.legsLost}L</div>
          <div className="stat-label">Legs</div>
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
          {showCopyRetry ? (
            <button
              onClick={retryClipboardCopy}
              disabled={copyingAI}
              className="btn btn-secondary"
              style={{ marginLeft: 'auto' }}
            >
              {copyingAI ? "Copying..." : "Retry Copy"}
            </button>
          ) : (
            <button
              onClick={copyForAI}
              disabled={copyingAI}
              className="btn btn-secondary"
              style={{ marginLeft: 'auto' }}
            >
              {copyingAI ? "Copying..." : "Copy for AI"}
            </button>
          )}
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
          {activeTab === "pending" && (
            <div className="filter-group">
              <button
                onClick={deleteAllPendingBets}
                disabled={loading || bets.filter(b => b.status === "pending").length === 0}
                className="btn btn-danger"
                style={{ marginRight: '1rem' }}
              >
                Delete All Pending
              </button>
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
        {betsByDay.map(([dateStr, dayBets, dayPnl, dayTotalStake]) => (
          <DaySection
            key={dateStr}
            dateStr={dateStr}
            dateLabel={getDateLabel(dateStr)}
            dayBets={dayBets}
            dayPnl={dayPnl}
            dayTotalStake={dayTotalStake}
            oddsFormat={oddsFormat}
            isCollapsed={collapsedDays[dateStr] || false}
            onToggleCollapse={() => {
              setCollapsedDays(prev => ({
                ...prev,
                [dateStr]: !prev[dateStr]
              }));
            }}
            expandedBets={expandedBets}
            onToggleBetExpand={(groupId, betId) => {
              const key = betId ? `${groupId}-${betId}` : groupId;
              setExpandedBets(prev => ({
                ...prev,
                [key]: !prev[key]
              }));
            }}
            onDelete={deletePendingBet}
          />
        ))}
        {betsByDay.length === 0 && !loading && (
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

function DaySection({ dateStr, dateLabel, dayBets, dayPnl, dayTotalStake, oddsFormat, isCollapsed, onToggleCollapse, expandedBets, onToggleBetExpand, onDelete }) {
  const pnlColor = dayPnl > 0 ? "#4CAF50" : dayPnl < 0 ? "#f44336" : "rgba(255, 255, 255, 0.5)";
  
  return (
    <div className="day-section">
      <div className="day-header">
        <button
          className="day-toggle"
          onClick={onToggleCollapse}
          aria-expanded={!isCollapsed}
        >
          {isCollapsed ? '▶' : '▼'} {dateLabel}
        </button>
        <div className="day-stats">
          <div className="day-stake" title="Total staked that day">
            ${dayTotalStake.toFixed(0)} staked
          </div>
          <div className="day-pnl" style={{ color: pnlColor }}>
            {dayPnl > 0 ? '+' : ''}{Math.round(dayPnl)} P&L
          </div>
        </div>
      </div>
      {!isCollapsed && (
        <div className="day-bets">
          {dayBets.map(([groupId, groupBets]) => (
            <BetGroup key={groupId} groupId={groupId} bets={groupBets} oddsFormat={oddsFormat} expandedBets={expandedBets} onToggleBetExpand={onToggleBetExpand} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

function BetGroup({ groupId, bets, oddsFormat, expandedBets, onToggleBetExpand, onDelete }) {
  const isParlay = bets.length > 1;
  const isExpanded = expandedBets[groupId] || false;
  
  let groupStatus = getGroupStatus(bets);
  const statusColor =
    groupStatus === "won"
      ? "#4CAF50"
      : groupStatus === "lost"
      ? "#f44336"
      : groupStatus === "void"
      ? "#9CA3AF"
      : "#FF9800";

  // Calculate total profit and stake
  // For parlays, only count the stake once (all legs have same original_stake)
  // For singles, sum all stakes
  let totalProfit = 0;
  let totalStake = 0;
  
  if (groupStatus === "void") {
    totalStake = 0;
    totalProfit = 0;
  } else if (isParlay) {
    // For parlay: use original_stake from first leg (it's the same for all)
    // If not available, multiply leg stake by number of legs
    totalStake = bets[0].original_stake || (bets[0].stake * bets.length) || 0;
    
    // For parlay profit, use decimal parlay odds
    if (groupStatus === "won") {
      totalProfit = calcParlayProfit(totalStake, bets[0].parlay_odds || 0);
    } else if (groupStatus === "lost") {
      totalProfit = -totalStake;
    }
  } else {
    // For singles: sum all stakes and profits
    bets.forEach((b) => {
      totalStake += (b.original_stake || b.stake || 0);
      if (b.status === "won") {
        totalProfit += calcAmericanProfit(b.original_stake || b.stake || 0, b.odds || 0);
      } else if (b.status === "lost") {
        totalProfit -= (b.original_stake || b.stake || 0);
      }
    });
  }
  
  if (!isFinite(totalProfit)) totalProfit = 0;
  if (!isFinite(totalStake)) totalStake = 0;

  return (
    <div className="bet-group">
      <button
        className="group-header"
        style={{ borderLeftColor: statusColor }}
        onClick={() => onToggleBetExpand(groupId, null)}
        aria-expanded={isExpanded}
      >
        <div className="group-toggle">{isExpanded ? '▼' : '▶'}</div>
        <div className="group-title">
          <span className="group-label">{isParlay ? `Parlay (${bets.length} legs)` : "Single"}</span>
          <span className="group-status" style={{ color: statusColor }}>
            {groupStatus.toUpperCase()}
          </span>
        </div>
        <div className="group-summary">
          <span>Stake: ${Math.round(totalStake)}</span>
          {totalProfit !== 0 && (
            <span style={{ color: totalProfit > 0 ? "#4CAF50" : "#f44336" }}>
              P&L: {totalProfit > 0 ? '+' : ''}${Math.round(totalProfit)}
            </span>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="group-content">
          {isParlay ? (
            <div className="parlay-legs">
              {bets.map((bet) => (
                <div key={bet.id} className="parlay-leg">
                  <BetCard bet={bet} oddsFormat={oddsFormat} onDelete={onDelete} />
                </div>
              ))}
            </div>
          ) : (
            <BetCard bet={bets[0]} oddsFormat={oddsFormat} onDelete={onDelete} />
          )}
        </div>
      )}
    </div>
  );
}

function BetCard({ bet, oddsFormat, onDelete }) {
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="bet-status" style={{ color: statusColor }}>
            {bet.status.toUpperCase()}
          </div>
          {bet.status === "pending" && onDelete && (
            <button
              onClick={() => onDelete(bet.id)}
              className="btn btn-small btn-danger"
              title="Delete this pending bet"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
            >
              Delete
            </button>
          )}
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
            <span>Date Placed:</span> <strong>{formatDate(bet.placed_at)}</strong>
          </div>
          <div className="detail-item">
            <span>Type:</span> <strong>{bet.bet_type}</strong>
          </div>
          <div className="detail-item">
            <span>Odds:</span> <strong>{formatOdds(bet.odds, oddsFormat)}</strong>
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
    // Display date in user's selected timezone
    return convertToUserTimezone(dateString, "date");
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