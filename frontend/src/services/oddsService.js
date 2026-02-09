/**
 * Odds conversion utility
 * Database stores American odds
 * Frontend can display either American or Decimal
 */

const ODDS_FORMAT_KEY = 'odds_format'; // 'american' or 'decimal'
const DEFAULT_FORMAT = 'american';

export function getOddsFormat() {
  return localStorage.getItem(ODDS_FORMAT_KEY) || DEFAULT_FORMAT;
}

export function setOddsFormat(format) {
  if (format === 'american' || format === 'decimal') {
    localStorage.setItem(ODDS_FORMAT_KEY, format);
    // Trigger a custom event so components can update
    window.dispatchEvent(new CustomEvent('oddsFormatChanged', { detail: { format } }));
  }
}

/**
 * Convert American odds to Decimal odds
 * @param americanOdds - odds in American format (e.g., -110, +200)
 * @returns decimal odds (e.g., 1.909, 3.0)
 */
export function americanToDecimal(americanOdds) {
  if (!americanOdds || americanOdds === 0) return 2.0; // default
  
  const odds = parseFloat(americanOdds);
  if (isNaN(odds)) return 2.0;
  
  if (odds > 0) {
    return (odds / 100 + 1).toFixed(3);
  } else {
    return (100 / Math.abs(odds) + 1).toFixed(3);
  }
}

/**
 * Convert Decimal odds to American odds
 * @param decimalOdds - odds in decimal format (e.g., 1.909, 3.0)
 * @returns American odds (e.g., -110, +200)
 */
export function decimalToAmerican(decimalOdds) {
  if (!decimalOdds || decimalOdds === 0) return -110; // default
  
  const odds = parseFloat(decimalOdds);
  if (isNaN(odds) || odds <= 1) return -110;
  
  const profit = odds - 1;
  
  if (profit >= 1) {
    return Math.round(profit * 100);
  } else {
    return Math.round(-100 / profit);
  }
}

/**
 * Format odds for display based on user preference
 * @param americanOdds - the odds in American format from database
 * @param format - optional format override ('american' or 'decimal')
 * @returns formatted odds string
 */
export function formatOdds(americanOdds, format = null) {
  const displayFormat = format || getOddsFormat();
  
  if (displayFormat === 'decimal') {
    const decimal = americanToDecimal(americanOdds);
    return `${decimal}`;
  } else {
    // American format
    const american = parseInt(americanOdds);
    if (american > 0) {
      return `+${american}`;
    } else {
      return `${american}`;
    }
  }
}

/**
 * Get label for odds format
 */
export function getOddsFormatLabel(format) {
  return format === 'decimal' ? 'Decimal (-110 = 1.91)' : 'American (-110, +200)';
}
