import React from 'react';
import './ErrorMessage.css';

/**
 * Reusable ErrorMessage component
 * Used across all pages for error states
 */
const ErrorMessage = React.memo(
  ({
    message,
    type = 'error', // 'error', 'warning', 'success', 'info'
    onRetry = null,
    onDismiss = null,
  }) => {
    const typeClass = `error-message error-message-${type}`;

    // Icon mapping
    const icons = {
      error: '❌',
      warning: '⚠️',
      success: '✅',
      info: 'ℹ️',
    };

    return (
      <div className={typeClass} role="alert">
        <div className="error-message-content">
          <span className="error-icon" aria-hidden="true">
            {icons[type]}
          </span>
          <span className="error-text">{message}</span>
        </div>

        <div className="error-actions">
          {onRetry && (
            <button className="error-btn error-btn-retry" onClick={onRetry} aria-label="Retry">
              Retry
            </button>
          )}
          {onDismiss && (
            <button
              className="error-btn error-btn-dismiss"
              onClick={onDismiss}
              aria-label="Dismiss"
            >
              ×
            </button>
          )}
        </div>
      </div>
    );
  }
);

ErrorMessage.displayName = 'ErrorMessage';

export default ErrorMessage;
