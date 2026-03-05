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

        <details className="ai-format-guide">
          <summary>📐 AI Format Guide — how to instruct your AI</summary>
          <div className="ai-format-guide-body">
            <p>
              After pasting the game data, tell your AI to respond using <strong>exactly</strong>{' '}
              the format below so the parser can read it correctly.
            </p>
            <p className="ai-format-guide-prompt">Suggested system / opening prompt:</p>
            <pre className="ai-format-guide-pre">{`When recommending bets, always respond using this exact format:

Parlay #N (X-leg [sport or "mixed"])
Sport: ..., Type: moneyline, Selection: [Team] ML, Game: [Away] vs [Home], Date: YYYY-MM-DD, Game ID: ..., Odds: X.XX, Stake: $XXX, Reason: ...
Sport: ..., Type: prop, Selection: [Player] Over/Under X.X [stat], Game: [Away] vs [Home], Date: YYYY-MM-DD, Game ID: ..., Odds: X.XX, Stake: $XXX, Reason: ...
Sport: ..., Type: total, Selection: [Teams] Over/Under X.X, Game: [Away] vs [Home], Date: YYYY-MM-DD, Game ID: ..., Odds: X.XX, Stake: $XXX, Reason: ...
Sport: ..., Type: spread, Selection: [Team] +/-X.X, Game: [Away] vs [Home], Date: YYYY-MM-DD, Game ID: ..., Odds: X.XX, Stake: $XXX, Reason: ...

Single Bet #N
Sport: ..., Type: spread, Selection: [Team] +/-X.X, Game: [Away] vs [Home], Date: YYYY-MM-DD, Game ID: ..., Odds: X.XX, Stake: $XXX, Reason: ...

Rules:
- Odds must be decimal (e.g. 1.91, not -110).
- Stake is the amount wagered per leg.
- Game ID must match the ID from the game data I provided.
- Do not deviate from this format — extra fields or missing commas will break parsing.`}</pre>
            <p className="ai-format-guide-note">
              <strong>Supported types:</strong> <code>moneyline</code>, <code>spread</code>,{' '}
              <code>total</code>, <code>prop</code>
            </p>
          </div>
        </details>
      </div>
    );
  }
);

BetInputSection.displayName = 'BetInputSection';

export default BetInputSection;
