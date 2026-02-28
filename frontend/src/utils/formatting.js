/**
 * Shared Formatting Utilities
 * Currency, numbers, percentages, etc.
 */

/**
 * Format currency value
 * @param {number} value - Amount to format
 * @param {boolean} showSign - Whether to show +/- sign
 * @param {boolean} round - Whether to round to nearest dollar
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value, showSign = false, round = true) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '$0';
  }

  const amount = round ? Math.round(value) : value;
  let sign = '';
  if (showSign) {
    if (amount > 0) {
      sign = '+';
    } else if (amount < 0) {
      sign = '-';
    }
  }

  return `${sign}$${Math.abs(amount).toLocaleString('en-US', {
    minimumFractionDigits: round ? 0 : 2,
    maximumFractionDigits: round ? 0 : 2,
  })}`;
};

/**
 * Format profit/loss with color indication
 * @param {number} value - P&L value
 * @returns {Object} { text: string, className: string, color: string }
 */
export const formatPnL = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return { text: '$0', className: 'neutral', color: '#999' };
  }

  const isProfit = value > 0;
  const isLoss = value < 0;

  return {
    text: formatCurrency(value, true, true),
    className: isProfit ? 'profit' : isLoss ? 'loss' : 'neutral',
    color: isProfit ? '#4CAF50' : isLoss ? '#f44336' : '#999',
  };
};

/**
 * Format percentage
 * @param {number} value - Percentage value (0-100)
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage string
 */
export const formatPercentage = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0%';
  }

  return `${value.toFixed(decimals)}%`;
};

/**
 * Format win rate with styling info
 * @param {number} wins - Number of wins
 * @param {number} total - Total number of bets
 * @returns {Object} { percentage: string, className: string }
 */
export const formatWinRate = (wins, total) => {
  if (!total || total === 0) {
    return { percentage: '0%', className: 'neutral' };
  }

  const rate = (wins / total) * 100;
  let className = 'neutral';

  if (rate >= 60) className = 'excellent';
  else if (rate >= 50) className = 'good';
  else if (rate >= 40) className = 'average';
  else className = 'poor';

  return {
    percentage: formatPercentage(rate, 1),
    className,
  };
};

/**
 * Format large numbers with K/M/B suffixes
 * @param {number} value - Number to format
 * @returns {string} Formatted string
 */
export const formatLargeNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0';
  }

  if (value >= 1000000000) {
    return `${(value / 1000000000).toFixed(1)}B`;
  }
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }

  return value.toFixed(0);
};

/**
 * Format ROI (Return on Investment)
 * @param {number} profit - Total profit
 * @param {number} stake - Total stake
 * @returns {Object} { percentage: string, className: string }
 */
export const formatROI = (profit, stake) => {
  if (!stake || stake === 0) {
    return { percentage: '0%', className: 'neutral' };
  }

  const roi = (profit / stake) * 100;
  let className = 'neutral';

  if (roi > 0) className = 'profit';
  else if (roi < 0) className = 'loss';

  return {
    percentage: `${roi > 0 ? '+' : ''}${roi.toFixed(1)}%`,
    className,
  };
};

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;

  return `${text.substring(0, maxLength)}...`;
};

/**
 * Format game score
 * @param {number} homeScore - Home team score
 * @param {number} awayScore - Away team score
 * @returns {string} Formatted score string
 */
export const formatScore = (homeScore, awayScore) => {
  if (homeScore === null || homeScore === undefined) return '-';
  if (awayScore === null || awayScore === undefined) return '-';

  return `${homeScore} - ${awayScore}`;
};

/**
 * Format team record (wins-losses)
 * @param {number} wins - Number of wins
 * @param {number} losses - Number of losses
 * @returns {string} Formatted record string
 */
export const formatRecord = (wins, losses) => {
  if (wins === null || wins === undefined) return '-';
  if (losses === null || losses === undefined) return '-';

  return `${wins}-${losses}`;
};

/**
 * Get status badge styling
 * @param {string} status - Status value
 * @returns {Object} { className: string, label: string }
 */
export const getStatusBadge = (status) => {
  const badges = {
    won: { className: 'status-won', label: 'Won' },
    lost: { className: 'status-lost', label: 'Lost' },
    pending: { className: 'status-pending', label: 'Pending' },
    void: { className: 'status-void', label: 'Void' },
    finished: { className: 'status-finished', label: 'Finished' },
    live: { className: 'status-live', label: 'Live' },
    scheduled: { className: 'status-scheduled', label: 'Scheduled' },
  };

  return (
    badges[status?.toLowerCase()] || { className: 'status-unknown', label: status || 'Unknown' }
  );
};

/**
 * Pluralize a word based on count
 * @param {number} count - Count value
 * @param {string} singular - Singular form
 * @param {string} plural - Plural form (optional, defaults to singular + 's')
 * @returns {string} Pluralized string
 */
export const pluralize = (count, singular, plural = null) => {
  if (count === 1) return singular;
  return plural || `${singular}s`;
};

/**
 * Format count with label
 * @param {number} count - Count value
 * @param {string} label - Label (will be pluralized)
 * @returns {string} Formatted string (e.g., "5 bets", "1 bet")
 */
export const formatCount = (count, label) => {
  return `${count} ${pluralize(count, label)}`;
};
