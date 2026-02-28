import React from 'react';
import { formatCurrency, formatPercentage } from '../utils/formatting';
import './BetStats.css';

const BetStats = React.memo(({ stats }) => {
  const { total, wins, losses, winRate, totalStake, totalPnl, roi } = stats;

  const statItems = [
    { label: 'Total Bets', value: total, className: 'neutral' },
    { label: 'Wins', value: wins, className: 'win' },
    { label: 'Losses', value: losses, className: 'loss' },
    {
      label: 'Win Rate',
      value: formatPercentage(winRate, 1),
      className: winRate >= 50 ? 'win' : 'loss',
    },
    { label: 'Total Staked', value: formatCurrency(totalStake, false, true), className: 'neutral' },
    {
      label: 'P&L',
      value: formatCurrency(totalPnl, true, true),
      className: totalPnl >= 0 ? 'win' : 'loss',
    },
    {
      label: 'ROI',
      value: `${roi >= 0 ? '+' : ''}${formatPercentage(roi, 1)}`,
      className: roi >= 0 ? 'win' : 'loss',
    },
  ];

  return (
    <div className="bet-stats">
      {statItems.map((item) => (
        <div key={item.label} className={`stat-item stat-${item.className}`}>
          <div className="stat-label">{item.label}</div>
          <div className="stat-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
});

BetStats.displayName = 'BetStats';

export default BetStats;
