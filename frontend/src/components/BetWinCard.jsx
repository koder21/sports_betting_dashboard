import React from 'react';
import './BetWinCard.css';

const BetWinCard = ({ betData }) => {
  // Parse the metadata
  const metadata = typeof betData.metadata === 'string' 
    ? JSON.parse(betData.metadata) 
    : betData.metadata;

  const { 
    selection, 
    odds, 
    stake, 
    profit, 
    bet_type,
    sport,
    game_info,
    status,
    legs 
  } = metadata;

  const isWon = status === 'won';

  const formatOdds = (odds) => {
    if (!odds) return 'N/A';
    const numOdds = parseFloat(odds);
    return numOdds > 0 ? `+${numOdds}` : numOdds.toString();
  };

  const formatMoney = (amount) => {
    if (amount === null || amount === undefined) return '$0.00';
    const num = parseFloat(amount);
    return num >= 0 ? `$${num.toFixed(2)}` : `-$${Math.abs(num).toFixed(2)}`;
  };

  return (
    <div className={`bet-win-card ${isWon ? 'won' : 'lost'}`}>
      <div className="bet-header">
        <div className="bet-badges">
          <span className="sport-badge">{sport?.toUpperCase() || 'BET'}</span>
          <span className="bet-type-badge">{bet_type || 'SINGLE'}</span>
        </div>
        <div className={`status-badge ${isWon ? 'won' : 'lost'}`}>
          {isWon ? '✓ WON' : '✗ LOST'}
        </div>
      </div>
      
      <div className="bet-content">
        <div className="bet-selection">
          <div className="selection-label">Selection</div>
          <div className="selection-value">{selection || 'N/A'}</div>
        </div>
        
        {game_info && (
          <div className="game-context">
            {game_info}
          </div>
        )}
        
        <div className="bet-details">
          <div className="bet-detail-item">
            <span className="detail-label">Odds</span>
            <span className="detail-value odds">{formatOdds(odds)}</span>
          </div>
          <div className="bet-detail-item">
            <span className="detail-label">Stake</span>
            <span className="detail-value">{formatMoney(stake)}</span>
          </div>
          <div className="bet-detail-item profit-item">
            <span className="detail-label">Profit</span>
            <span className={`detail-value profit ${profit >= 0 ? 'positive' : 'negative'}`}>
              {formatMoney(profit)}
            </span>
          </div>
        </div>
        
        {legs && legs.length > 0 && (
          <div className="parlay-legs">
            <div className="legs-label">Legs:</div>
            {legs.map((leg, idx) => (
              <div key={idx} className="leg-item">
                <span className={`leg-status ${leg.status}`}>{leg.status === 'won' ? '✓' : '✗'}</span>
                <span className="leg-selection">{leg.selection}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="bet-footer">
        <span className="bet-time">
          {new Date(betData.created_at).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
          })}
        </span>
      </div>
    </div>
  );
};

export default BetWinCard;
