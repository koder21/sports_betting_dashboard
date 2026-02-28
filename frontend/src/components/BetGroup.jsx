import React from 'react';
import BetCard from './BetCard.jsx';
import { formatCurrency, getStatusBadge } from '../utils/formatting';
import { formatOdds } from '../services/oddsService';
import './BetGroup.css';

const BetGroup = React.memo(({ group, oddsFormat, isExpanded, onToggleExpansion, onDelete }) => {
  const { bets, isParlay, status, stake, pnl } = group;
  const statusBadge = getStatusBadge(status);

  if (isParlay) {
    // Parlay display
    // Debug/copy handler
    const handleCopyDebug = () => {
      const parlayInfo = {
        parlay_id: bets[0]?.parlay_id,
        bet_count: bets.length,
        legs: bets.map((bet) => ({
          id: bet.id,
          selection: bet.selection,
          odds: bet.odds,
          stake: bet.stake,
          status: bet.status,
          profit: bet.profit,
          bet_type: bet.bet_type,
          game_id: bet.game_id,
          player_id: bet.player_id,
          result_value: bet.result_value,
          final_score: bet.final_score,
        })),
      };
      navigator.clipboard.writeText(JSON.stringify(parlayInfo, null, 2));
    };
    return (
      <div className={`bet-group bet-group-parlay bet-group-${status}`}>
        <div className="bet-group-header">
          <div className="group-title">
            <span className="parlay-icon" aria-hidden="true">
              📊
            </span>
            <span className="parlay-label">{bets.length}-Leg Parlay</span>
            <span className={`status-badge ${statusBadge.className}`}>{statusBadge.label}</span>
          </div>
          <div className="group-actions">
            <button
              className="debug-copy-btn"
              title={
                bets[0]?.parlay_id
                  ? `Copy debug info for parlay\nParlay ID: ${bets[0].parlay_id}`
                  : 'Copy debug info'
              }
              onClick={handleCopyDebug}
              style={{ marginRight: 8, cursor: 'pointer' }}
            >
              🐞
            </button>
            <button className="delete-group-btn" onClick={onDelete} aria-label="Delete parlay">
              🗑️
            </button>
          </div>
        </div>

        <div className="parlay-summary">
          <div className="summary-stat">
            <span className="summary-label">Stake</span>
            <span className="summary-value">{formatCurrency(stake, false, true)}</span>
          </div>
          <div className="summary-stat">
            <span className="summary-label">Odds</span>
            <span className="summary-value">{formatOdds(bets[0].parlay_odds, oddsFormat)}</span>
          </div>
          {pnl !== 0 && (
            <div className="summary-stat">
              <span className="summary-label">P&L</span>
              <span className={`summary-value ${pnl >= 0 ? 'profit' : 'loss'}`}>
                {formatCurrency(pnl, true, true)}
              </span>
            </div>
          )}
        </div>

        <div className="parlay-legs">
          <div className="legs-header">Legs:</div>
          {bets.map((bet, index) => (
            <div key={bet.id} className={`parlay-leg leg-${bet.status}`}>
              <span className="leg-number">{index + 1}</span>
              <span className="leg-selection">{bet.selection || bet.pick}</span>
              {/* Show result for each leg: final score for moneyline/spread, stat for prop */}
              {bet.bet_type === 'moneyline' || bet.bet_type === 'spread' ? (
                bet.final_score ? (
                  <span className="leg-result">
                    {' '}
                    — Final: {bet.final_score.replace('Final:', '').trim()}
                  </span>
                ) : null
              ) : bet.bet_type === 'prop' &&
                bet.result_value !== undefined &&
                bet.result_value !== null ? (
                <span className="leg-result">
                  {' '}
                  — Result: {bet.result_value} {bet.stat_type ? bet.stat_type : ''}
                </span>
              ) : null}
              <span className="leg-odds">{formatOdds(bet.odds, oddsFormat)}</span>
              <span className={`leg-status status-${bet.status}`}>{bet.status}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Single bet display
  return (
    <BetCard
      bet={bets[0]}
      oddsFormat={oddsFormat}
      showDetails={true}
      isExpanded={isExpanded}
      onExpand={onToggleExpansion}
      onDelete={onDelete}
    />
  );
});

BetGroup.displayName = 'BetGroup';

export default BetGroup;
