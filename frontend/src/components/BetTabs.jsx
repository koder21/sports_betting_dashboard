import React from 'react';
import './BetTabs.css';

const BetTabs = React.memo(({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'pending', label: 'Pending', icon: '⏳' },
    { id: 'finished', label: 'Finished', icon: '✅' },
    { id: 'voided', label: 'Voided', icon: '🚫' },
  ];

  return (
    <div className="bet-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-label={`${tab.label} bets tab`}
          className={`bet-tab ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="tab-icon" aria-hidden="true">
            {tab.icon}
          </span>
          <span className="tab-label">{tab.label}</span>
        </button>
      ))}
    </div>
  );
});

BetTabs.displayName = 'BetTabs';

export default BetTabs;
