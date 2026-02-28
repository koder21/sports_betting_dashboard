import React from 'react';
import './BetInputSection.css';

const BetInputSection = React.memo(
  ({
    rawText,
    onTextChange,
    onPlaceBets,
    onCopyForAI,
    onRetryClipboardCopy,
    onDeleteAllPending,
    loading,
    copyingAI,
    showCopyRetry,
    activeTab,
    pendingCount,
  }) => {
    return (
      <div className="bet-input-section">
        <h2>Place New Bets</h2>
        <textarea
          value={rawText}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder={`Parlay #1 (2 legs)
Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-07, Game ID: 123, Odds: -150, Stake: 300, Reason: Strong matchup.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-07, Game ID: 456, Odds: -110, Stake: 300, Reason: High usage.

Singles
Type: spread, Selection: Lakers -5.5, Game: Lakers vs Suns, Date: 2026-02-08, Game ID: 789, Odds: -110, Stake: 100, Reason: Home advantage.`}
          rows={8}
          className="bet-textarea"
          aria-label="Enter bet details"
        />

        <div className="button-group">
          <button
            onClick={onPlaceBets}
            disabled={loading || !rawText.trim()}
            className="btn btn-primary"
            aria-label="Place bets from text input"
          >
            {loading ? 'Processing...' : 'Place Bets'}
          </button>

          {showCopyRetry ? (
            <button
              onClick={onRetryClipboardCopy}
              disabled={copyingAI}
              className="btn btn-secondary copy-ai-btn"
              aria-label="Retry copying AI context to clipboard"
            >
              {copyingAI ? 'Copying...' : '🔄 Retry Copy'}
            </button>
          ) : (
            <button
              onClick={onCopyForAI}
              disabled={copyingAI}
              className="btn btn-secondary copy-ai-btn"
              aria-label="Copy game context for AI analysis"
            >
              {copyingAI ? 'Copying...' : '📋 Copy for AI'}
            </button>
          )}

          {activeTab === 'pending' && pendingCount > 0 && (
            <button
              onClick={onDeleteAllPending}
              disabled={loading}
              className="btn btn-danger"
              aria-label={`Delete all ${pendingCount} pending bets`}
            >
              🗑️ Delete All Pending ({pendingCount})
            </button>
          )}
        </div>

        <div className="input-helper-text">
          <strong>Tip:</strong> Click "Copy for AI" to get fresh game data, then paste it into an AI
          chat to get betting recommendations. Paste the AI's recommendations here and click "Place
          Bets".
        </div>
      </div>
    );
  }
);

BetInputSection.displayName = 'BetInputSection';

export default BetInputSection;
