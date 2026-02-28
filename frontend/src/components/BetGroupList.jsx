import React from 'react';
import BetGroup from './BetGroup.jsx';
import { getFriendlyDateLabel } from '../utils/dateFormatting';
import { formatCurrency } from '../utils/formatting';
import './BetGroupList.css';

const BetGroupList = React.memo(
  ({
    betsByDay,
    collapsedDays,
    expandedBets,
    oddsFormat,
    onToggleDay,
    onToggleExpansion,
    onDeleteGroup,
  }) => {
    if (betsByDay.length === 0) {
      return (
        <div className="no-bets">
          <p>No bets found</p>
        </div>
      );
    }

    return (
      <div className="bet-group-list">
        {betsByDay.map(({ date, groups, stake, pnl }) => {
          const isCollapsed = collapsedDays[date];
          const dateLabel = getFriendlyDateLabel(date);

          return (
            <div key={date} className="day-section">
              {/* Day Header */}
              <button
                className="day-header"
                onClick={() => onToggleDay(date)}
                aria-expanded={!isCollapsed}
                aria-label={`${dateLabel} - ${isCollapsed ? 'Expand' : 'Collapse'}`}
              >
                <div className="day-info">
                  <span className="day-label">{dateLabel}</span>
                  <span className="day-count">
                    {groups.length} bet{groups.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="day-stats">
                  <span className="day-stake">Staked: {formatCurrency(stake, false, true)}</span>
                  <span className={`day-pnl ${pnl >= 0 ? 'profit' : 'loss'}`}>
                    {formatCurrency(pnl, true, true)}
                  </span>
                  <span className="collapse-icon">{isCollapsed ? '▶' : '▼'}</span>
                </div>
              </button>

              {/* Day Bets */}
              {!isCollapsed && (
                <div className="day-bets">
                  {groups.map((group) => (
                    <BetGroup
                      key={group.parlay_id || `single-${group.bets[0].id}`}
                      group={group}
                      oddsFormat={oddsFormat}
                      isExpanded={expandedBets[group.bets[0].id]}
                      onToggleExpansion={() => onToggleExpansion(group.bets[0].id)}
                      onDelete={() => onDeleteGroup(group)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }
);

BetGroupList.displayName = 'BetGroupList';

export default BetGroupList;
