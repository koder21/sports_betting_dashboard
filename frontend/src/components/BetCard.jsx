import React from 'react';
import { formatDate } from '../utils/dateFormatting';
import { formatCurrency, getStatusBadge } from '../utils/formatting';
import { formatOdds } from '../services/oddsService';
import './BetCard.css';

/**
 * Reusable BetCard component
 * Used in BetsPage, AAIBetsPage, and other bet displays
 */
const BetCard = React.memo(
  ({
    bet,
    oddsFormat = 'american',
    showDetails = false,
    onDelete = null,
    onExpand = null,
    isExpanded = false,
  }) => {
    const statusBadge = getStatusBadge(bet.status);

    // Get stat label for display
    const getStatLabel = () => {
      if (!bet.stat_type) return '';
      const labels = {
        points: 'pts',
        rebounds: 'reb',
        assists: 'ast',
        passing_yards: 'pass yds',
        rushing_yards: 'rush yds',
        receiving_yards: 'rec yds',
      };
      return labels[bet.stat_type] || bet.stat_type;
    };

    const statLabel = getStatLabel();

    const isFinished = ['won', 'lost', 'void', 'finished'].includes(bet.status);
    // Debug/copy handler for single bet
    const handleCopyDebug = () => {
      const betInfo = {
        bet_id: bet.id,
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
        reason: bet.reason,
        stat_type: bet.stat_type,
        market: bet.market,
        placed_at: bet.placed_at,
        graded_at: bet.graded_at,
      };
      navigator.clipboard.writeText(JSON.stringify(betInfo, null, 2));
    };
    return (
      <div className={`bet-card ${bet.status}`}>
        {/* Header */}
        <div className="bet-card-header">
          <div className="bet-card-title">
            <span className="bet-selection">{bet.selection || bet.pick}</span>
            <span className={`status-badge ${statusBadge.className}`}>{statusBadge.label}</span>
          </div>
          <div className="bet-card-actions">
            <button
              className="debug-copy-btn"
              title={bet.id ? `Copy debug info for bet\nBet ID: ${bet.id}` : 'Copy debug info'}
              onClick={handleCopyDebug}
              style={{ marginRight: 8, cursor: 'pointer' }}
            >
              🐞
            </button>
            {onDelete && (
              <button
                className="bet-card-delete"
                onClick={() => onDelete(bet.id)}
                aria-label="Delete bet"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Main Info */}
        <div className="bet-card-body">
          {/* Final Score for finished bets */}
          {isFinished && bet.final_score && (
            <div className="bet-final-score">
              <span className="final-score-label">Final Score:</span>
              <span className="final-score-value">
                {bet.final_score.replace('Final:', '').trim()}
              </span>
            </div>
          )}
          {/* Game Info */}
          {bet.game && (
            <div className="bet-game-info">
              <div className="game-matchup">
                {bet.game.away_team} @ {bet.game.home_team}
              </div>
              {bet.game.status !== 'scheduled' && (
                <div className="game-score">
                  {bet.game.away_score} - {bet.game.home_score}
                </div>
              )}
            </div>
          )}

          {/* Player Info */}
          {(bet.player || bet.player_name) && (
            <div className="bet-player-info">
              <span className="player-icon" aria-hidden="true">
                👤
              </span>
              <span className="player-name">{bet.player?.name || bet.player_name}</span>
            </div>
          )}

          {/* Bet Stats */}
          <div className="bet-stats">
            <div className="bet-stat">
              <span className="stat-label">Stake</span>
              <span className="stat-value">{formatCurrency(bet.stake, false, true)}</span>
            </div>
            <div className="bet-stat">
              <span className="stat-label">Odds</span>
              <span className="stat-value">{formatOdds(bet.odds, oddsFormat)}</span>
            </div>
            {/* Show result_value for prop bets, or fallback to final_score if result_value is missing */}
            {bet.bet_type === 'prop' &&
              (bet.result_value !== null && bet.result_value !== undefined ? (
                <div className="bet-stat">
                  <span className="stat-label">Result</span>
                  <span className={`stat-value result-${bet.status}`}>
                    {bet.result_value}
                    {statLabel ? ` ${statLabel}` : ''}
                  </span>
                </div>
              ) : bet.final_score ? (
                <div className="bet-stat">
                  <span className="stat-label">Result</span>
                  <span className={`stat-value result-${bet.status}`}>
                    {bet.final_score}
                    {statLabel ? ` ${statLabel}` : ''}
                  </span>
                </div>
              ) : null)}
            {bet.profit !== null && bet.profit !== undefined && (
              <div className="bet-stat">
                <span className="stat-label">Profit</span>
                <span className={`stat-value profit-${bet.profit > 0 ? 'positive' : 'negative'}`}>
                  {formatCurrency(bet.profit, true, true)}
                </span>
              </div>
            )}
          </div>

          {/* Reason/Notes */}
          {bet.reason && (
            <div className="bet-reason">
              <em>{bet.reason}</em>
            </div>
          )}

          {/* Date */}
          <div className="bet-date">
            <span className="date-icon" aria-hidden="true">
              📅
            </span>
            {formatDate(bet.placed_at, 'datetime')}
          </div>
        </div>

        {/* Expandable Details */}
        {showDetails && onExpand && (
          <button
            className="bet-expand-toggle"
            onClick={() => onExpand(bet.id)}
            aria-label={isExpanded ? 'Hide details' : 'Show details'}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Hide Details' : 'Show Details'}
          </button>
        )}

        {isExpanded && showDetails && (
          <div className="bet-details-expanded">
            <div className="detail-row">
              <span className="detail-label">Bet Type:</span>
              <span className="detail-value">{bet.bet_type}</span>
            </div>
            {bet.market && (
              <div className="detail-row">
                <span className="detail-label">Market:</span>
                <span className="detail-value">{bet.market}</span>
              </div>
            )}
            {bet.game_id && (
              <div className="detail-row">
                <span className="detail-label">Game ID:</span>
                <span className="detail-value monospace">{bet.game_id}</span>
              </div>
            )}
            {bet.graded_at && (
              <div className="detail-row">
                <span className="detail-label">Graded:</span>
                <span className="detail-value">{formatDate(bet.graded_at, 'datetime')}</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

BetCard.displayName = 'BetCard';

export default BetCard;
