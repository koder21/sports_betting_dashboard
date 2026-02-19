import React from 'react';
import './BetFilters.css';

const BetFilters = React.memo(({
  activeTab,
  showWins,
  showLosses,
  dateFilter,
  onShowWinsChange,
  onShowLossesChange,
  onDateFilterChange,
}) => {
  return (
    <div className="bet-filters">
      {/* Win/Loss Filters (only for finished tab) */}
      {activeTab === 'finished' && (
        <div className="filter-group">
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={showWins}
              onChange={(e) => onShowWinsChange(e.target.checked)}
              aria-label="Show wins"
            />
            <span className="checkbox-label win">Show Wins</span>
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={showLosses}
              onChange={(e) => onShowLossesChange(e.target.checked)}
              aria-label="Show losses"
            />
            <span className="checkbox-label loss">Show Losses</span>
          </label>
        </div>
      )}

      {/* Date Filter */}
      <div className="filter-group">
        <label htmlFor="date-filter" className="filter-label">
          Filter by Date:
        </label>
        <input
          id="date-filter"
          type="date"
          value={dateFilter}
          onChange={(e) => onDateFilterChange(e.target.value)}
          className="date-input"
          aria-label="Filter bets by date"
        />
        {dateFilter && (
          <button
            className="clear-filter-btn"
            onClick={() => onDateFilterChange('')}
            aria-label="Clear date filter"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
});

BetFilters.displayName = 'BetFilters';

export default BetFilters;
