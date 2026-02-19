import React, { useState, useEffect, useMemo, useCallback } from "react";
import api from "../services/api.js";
import { getOddsFormat, americanToDecimal, decimalToAmerican } from "../services/oddsService.js";
import { groupBetsByParlay } from "../utils/betCalculations.js";
import { groupByDate } from "../utils/dateFormatting.js";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import BetTabs from "../components/BetTabs.jsx";
import BetFilters from "../components/BetFilters.jsx";
import BetGroupList from "../components/BetGroupList.jsx";
import BetStats from "../components/BetStats.jsx";
import VerificationModal from "../components/VerificationModal.jsx";
import BetInputSection from "../components/BetInputSection.jsx";
import "./BetsPage.css";

// Constants
const DEFAULT_TAB = "pending";
const POLL_INTERVAL = 30000; // 30 seconds

function BetsPage() {
    // Pagination for finished bets: show only N days, with 'load more'
    const DAYS_PER_PAGE = 10;
    const [daysShown, setDaysShown] = useState(DAYS_PER_PAGE);
  // State
  const [rawText, setRawText] = useState("");
  const [bets, setBets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [copyingAI, setCopyingAI] = useState(false);
  const [error, setError] = useState(null);
  const [oddsFormat, setOddsFormat] = useState(getOddsFormat());
  const [activeTab, setActiveTab] = useState(DEFAULT_TAB);
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

  // Fetch bets on mount and poll
  useEffect(() => {
    fetchBets();
    const interval = setInterval(fetchBets, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // Listen for odds format changes
  useEffect(() => {
    const handleOddsFormatChange = (e) => {
      setOddsFormat(e.detail.format);
    };
    window.addEventListener('oddsFormatChanged', handleOddsFormatChange);
    return () => window.removeEventListener('oddsFormatChanged', handleOddsFormatChange);
  }, []);

  // Fetch bets from API
  const fetchBets = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get("/api/bets/all");
      if (response.data.bets) {
        setBets(response.data.bets);
      }
    } catch (err) {
      setError("Failed to fetch bets. Please try again.");
      console.error('Fetch bets error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Copy for AI function
  const copyForAI = useCallback(async () => {
    setCopyingAI(true);
    setError(null);
    setShowCopyRetry(false);

    try {
      setError("🔄 Fetching fresh data (games, results, injuries)...");
      const response = await api.get("/api/games/ai-context-fresh");
      
      if (response.data.text) {
        setAiContextData(response.data);
        
        if (response.data.scrape_errors && response.data.scrape_errors.length > 0) {
          setError('⚠️ Scrape errors: ' + response.data.scrape_errors.join('; '));
        }
        
        try {
          await navigator.clipboard.writeText(response.data.text);
          setError(`✓ Copied ${response.data.yesterday_count} yesterday's results and ${response.data.today_count} upcoming games with fresh data!`);
          setTimeout(() => setError(null), 3000);
        } catch (clipboardErr) {
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
    } finally {
      setCopyingAI(false);
    }
  }, []);

  // Retry clipboard copy
  const retryClipboardCopy = useCallback(async () => {
    if (!aiContextData) {
      setError("No data to copy. Please fetch again.");
      return;
    }
    
    setCopyingAI(true);
    setError(null);
    
    try {
      await navigator.clipboard.writeText(aiContextData.text);
      setError(`✓ Copied ${aiContextData.yesterday_count} yesterday's results and ${aiContextData.today_count} upcoming games!`);
      setShowCopyRetry(false);
      setTimeout(() => setError(null), 3000);
      
      if (aiContextData.scrape_errors && aiContextData.scrape_errors.length > 0) {
        setError('⚠️ Scrape errors: ' + aiContextData.scrape_errors.join('; '));
      }
    } catch (err) {
      setError("Failed to copy to clipboard: " + err.message);
    } finally {
      setCopyingAI(false);
    }
  }, [aiContextData]);

  // Parse bet text into structured format
  const parseBetText = useCallback((text) => {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l);
    const groups = [];
    let currentGroup = null;
    let singles = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (/^Parlay/i.test(line)) {
        if (currentGroup) groups.push(currentGroup);
        currentGroup = { legs: [], stake: null, sport: 'NCAAB' };
      } else if (/^Singles/i.test(line)) {
        if (currentGroup) groups.push(currentGroup);
        currentGroup = null;
      } else if (/^Type:/i.test(line)) {
        const leg = {};
        const typeMatch = line.match(/Type:\s*([^,]+)/i);
        const selectionMatch = line.match(/Selection:\s*([^,]+)/i);
        const gameMatch = line.match(/Game:\s*([^,]+)/i);
        const dateMatch = line.match(/Date:\s*([^,]+)/i);
        const gameIdMatch = line.match(/Game ID:\s*([^,]+)/i);
        const oddsMatch = line.match(/Odds:\s*([^,]+)/i);
        const stakeMatch = line.match(/Stake:\s*([^,]+)/i);
        const reasonMatch = line.match(/Reason:\s*(.*)$/i);

        leg.bet_type = typeMatch ? typeMatch[1].trim() : '';
        leg.selection = selectionMatch ? selectionMatch[1].trim() : '';
        leg.game = gameMatch ? gameMatch[1].trim() : '';
        leg.date = dateMatch ? dateMatch[1].trim() : '';
        leg.game_id = gameIdMatch ? gameIdMatch[1].trim() : '';
        
        // Detect decimal odds and convert to American odds for storage
        let rawOdds = oddsMatch ? oddsMatch[1].trim() : null;
        let oddsNum = rawOdds ? parseFloat(rawOdds) : null;
        if (oddsNum !== null) {
          if (oddsNum >= 1.01 && oddsNum < 20) {
            // Decimal odds, convert to American
            leg.odds = decimalToAmerican(oddsNum);
          } else {
            // Assume American odds
            leg.odds = oddsNum;
          }
        } else {
          leg.odds = null;
        }
        
        leg.stake = stakeMatch ? parseFloat(stakeMatch[1].trim()) : null;
        leg.reason = reasonMatch ? reasonMatch[1].trim() : '';
        leg.sport = 'NCAAB';

        if (currentGroup) {
          currentGroup.legs.push(leg);
          if (!currentGroup.stake && leg.stake) currentGroup.stake = leg.stake;
        } else {
          singles.push(leg);
        }
      }
    }
    
    if (currentGroup) groups.push(currentGroup);
    return { parlays: groups.filter(g => g.legs.length > 1), singles };
  }, []);

  // Place bets from textarea
  const placeBets = useCallback(async () => {
    if (!rawText.trim()) {
      setError("Please enter bet details");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const parsed = parseBetText(rawText);
      let errors = [];

      // Place parlays
      for (const parlay of parsed.parlays) {
        const payload = {
          legs: parlay.legs.map(leg => ({
            game_id: leg.game_id,
            pick: leg.selection,
            odds: leg.odds,
            confidence: 0,
            reason: leg.reason
          })),
          stake: parlay.stake,
          sport: parlay.legs[0]?.sport || 'NCAAB'
        };
        
        try {
          const resp = await api.post("/bets/place-aai-parlay", payload);
          if (!resp.data.success) errors.push(resp.data.error || 'Failed to place parlay');
        } catch (err) {
          errors.push(err.response?.data?.detail || err.message);
        }
      }

      // Place singles
      for (const leg of parsed.singles) {
        const payload = {
          game_id: leg.game_id,
          pick: leg.selection,
          confidence: 0,
          combined_confidence: 0,
          stake: leg.stake,
          odds: leg.odds,
          reason: leg.reason,
          sport: leg.sport || 'NCAAB'
        };
        
        try {
          const resp = await api.post("/bets/place-aai-single", payload);
          if (!resp.data.success) errors.push(resp.data.error || 'Failed to place single');
        } catch (err) {
          errors.push(err.response?.data?.detail || err.message);
        }
      }

      setRawText("");
      await fetchBets();
      
      if (errors.length > 0) {
        setError(errors.join("\n"));
      } else {
        setError("✓ Bets placed successfully");
        setTimeout(() => setError(null), 3000);
      }
    } catch (err) {
      setError("Error placing bets: " + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  }, [rawText, parseBetText, fetchBets]);

  // Delete all pending bets
  const deleteAllPendingBets = useCallback(async () => {
    if (!window.confirm("Delete ALL pending bets? This cannot be undone.")) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.delete("/api/bets/pending-all");
      
      if (response.data.status === "ok") {
        const deletedCount = response.data.deleted || 0;
        setError(`✓ ${deletedCount} pending bet${deletedCount !== 1 ? 's' : ''} deleted`);
        setTimeout(() => setError(null), 3000);
        await fetchBets();
      }
    } catch (err) {
      setError("Error deleting pending bets: " + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  }, [fetchBets]);

  // Group and filter bets (same as before)
  const groupedBets = useMemo(() => groupBetsByParlay(bets), [bets]);

  const tabFilteredBets = useMemo(() => {
    if (activeTab === "pending") {
      return groupedBets.filter(g => g.status === "pending");
    } else if (activeTab === "finished") {
      return groupedBets.filter(g => ["won", "lost"].includes(g.status));
    } else if (activeTab === "voided") {
      return groupedBets.filter(g => g.status === "void");
    }
    return groupedBets;
  }, [groupedBets, activeTab]);

  const winLossFilteredBets = useMemo(() => {
    if (activeTab !== "finished") return tabFilteredBets;
    return tabFilteredBets.filter(group => {
      if (!showWins && group.status === "won") return false;
      if (!showLosses && group.status === "lost") return false;
      return true;
    });
  }, [tabFilteredBets, activeTab, showWins, showLosses]);

  const dateFilteredBets = useMemo(() => {
    if (!dateFilter) return winLossFilteredBets;
    const filterDate = new Date(dateFilter).toISOString().split('T')[0];
    return winLossFilteredBets.filter(group => {
      const groupDate = new Date(group.placed_at).toISOString().split('T')[0];
      return groupDate === filterDate;
    });
  }, [winLossFilteredBets, dateFilter]);

  const betsByDay = useMemo(() => {
    const grouped = groupByDate(dateFilteredBets, 'placed_at');
    const allDays = Object.entries(grouped)
      .sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA))
      .map(([date, groups]) => {
        const dayStats = groups.reduce((acc, group) => {
          acc.stake += group.stake;
          acc.pnl += group.pnl;
          return acc;
        }, { stake: 0, pnl: 0 });
        return { date, groups, ...dayStats };
      });
    // Only paginate for finished tab
    if (activeTab === "finished") {
      return allDays.slice(0, daysShown);
    }
    return allDays;
  }, [dateFilteredBets, activeTab, daysShown]);
  // Handler for loading more days
  const handleLoadMoreDays = () => setDaysShown(s => s + DAYS_PER_PAGE);

  // No auto-collapse: days only collapse/expand when user clicks

  const toggleDayCollapse = useCallback((date) => {
    setCollapsedDays(prev => ({ ...prev, [date]: !prev[date] }));
  }, []);

  const toggleBetExpansion = useCallback((betId) => {
    setExpandedBets(prev => ({ ...prev, [betId]: !prev[betId] }));
  }, []);

  const deleteBetGroup = useCallback(async (group) => {
    const isParlay = group.isParlay;
    
    if (!window.confirm(`Delete this ${isParlay ? 'parlay' : 'bet'}? This cannot be undone.`)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (isParlay && group.parlay_id) {
        await api.delete(`/api/bets/parlay/${group.parlay_id}`);
      } else {
        const bet = group.bets[0];
        const endpoint = ["won", "lost", "finished"].includes(bet.status)
          ? `/api/bets/finished/${bet.id}`
          : `/api/bets/pending/${bet.id}`;
        await api.delete(endpoint);
      }
      
      setError("✓ Bet deleted successfully");
      setTimeout(() => setError(null), 3000);
      await fetchBets();
    } catch (err) {
      setError(`Failed to delete bet: ${err.response?.data?.message || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [fetchBets]);

  const verifyBets = useCallback(async () => {
    setVerifying(true);
    setError(null);

    try {
      const response = await api.post("/api/bets/verify");
      setVerificationResults(response.data);
      
      if (response.data.discrepancies_found > 0) {
        setShowVerificationModal(true);
      } else {
        setError("✓ All bets verified correctly!");
        setTimeout(() => setError(null), 5000);
      }
    } catch (err) {
      setError(`Verification failed: ${err.response?.data?.message || err.message}`);
    } finally {
      setVerifying(false);
    }
  }, []);

  const applyCorrections = useCallback(async (corrections) => {
    setLoading(true);
    setError(null);

    try {
      await api.post("/api/bets/apply-corrections", { corrections });
      setError("✓ Corrections applied successfully");
      setTimeout(() => setError(null), 3000);
      setShowVerificationModal(false);
      await fetchBets();
    } catch (err) {
      setError(`Failed to apply corrections: ${err.response?.data?.message || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [fetchBets]);

  const overallStats = useMemo(() => {
    const finished = groupedBets.filter(g => ["won", "lost"].includes(g.status));
    const wins = finished.filter(g => g.status === "won").length;
    const totalStake = finished.reduce((sum, g) => sum + g.stake, 0);
    const totalPnl = finished.reduce((sum, g) => sum + g.pnl, 0);
    
    return {
      total: finished.length,
      wins,
      losses: finished.length - wins,
      winRate: finished.length > 0 ? (wins / finished.length) * 100 : 0,
      totalStake,
      totalPnl,
      roi: totalStake > 0 ? (totalPnl / totalStake) * 100 : 0,
    };
  }, [groupedBets]);

  if (loading && bets.length === 0) {
    return <LoadingSpinner fullPage message="Loading bets..." />;
  }

  return (
    <div className="bets-page">
      <div className="bets-header">
        <h1>Betting Tracker</h1>
        <button 
          className="verify-btn"
          onClick={verifyBets}
          disabled={verifying || loading}
        >
          {verifying ? "Verifying..." : "🔍 Verify Bets"}
        </button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          type={error.startsWith("✓") ? "success" : "error"}
          onDismiss={() => setError(null)}
        />
      )}

      <BetStats stats={overallStats} />

      {/* Input Section for Pasting Bets */}
      <BetInputSection
        rawText={rawText}
        onTextChange={setRawText}
        onPlaceBets={placeBets}
        onCopyForAI={copyForAI}
        onRetryClipboardCopy={retryClipboardCopy}
        onDeleteAllPending={deleteAllPendingBets}
        loading={loading}
        copyingAI={copyingAI}
        showCopyRetry={showCopyRetry}
        activeTab={activeTab}
        pendingCount={bets.filter(b => b.status === "pending").length}
      />

      <BetTabs activeTab={activeTab} onTabChange={setActiveTab} />

      <BetFilters
        activeTab={activeTab}
        showWins={showWins}
        showLosses={showLosses}
        dateFilter={dateFilter}
        onShowWinsChange={setShowWins}
        onShowLossesChange={setShowLosses}
        onDateFilterChange={setDateFilter}
      />

      {loading && bets.length > 0 && (
        <div className="inline-loading">
          <LoadingSpinner size="small" message="Refreshing..." />
        </div>
      )}

      <BetGroupList
        betsByDay={betsByDay}
        collapsedDays={collapsedDays}
        expandedBets={expandedBets}
        oddsFormat={oddsFormat}
        onToggleDay={toggleDayCollapse}
        onToggleExpansion={toggleBetExpansion}
        onDeleteGroup={deleteBetGroup}
      />

          {/* Load more days for finished bets */}
          {activeTab === "finished" && betsByDay.length < Object.keys(groupByDate(dateFilteredBets, 'placed_at')).length && (
            <div style={{ textAlign: 'center', margin: '1.5em 0' }}>
              <button className="load-more-btn" onClick={handleLoadMoreDays}>
                Load More Days
              </button>
            </div>
          )}

      {showVerificationModal && verificationResults && (
        <VerificationModal
          results={verificationResults}
          onClose={() => setShowVerificationModal(false)}
          onApply={applyCorrections}
        />
      )}
    </div>
  );
}

export default BetsPage;