/**
 * Shared Bet Calculation Utilities
 * Used across BetsPage, AAIBetsPage, and analytics pages
 */

/**
 * Calculate profit from American odds
 * @param {number} stake - Bet amount
 * @param {number} odds - American odds (e.g., -110, +200)
 * @returns {number} Profit amount
 */
export const calcAmericanProfit = (stake, odds) => {
  if (!odds || stake === 0) return 0;
  if (odds > 0) return stake * (odds / 100);
  return stake / (Math.abs(odds) / 100);
};

/**
 * Calculate profit from decimal odds
 * @param {number} stake - Bet amount
 * @param {number} decimalOdds - Decimal odds (e.g., 1.91, 3.0)
 * @returns {number} Profit amount
 */
export const calcDecimalProfit = (stake, decimalOdds) => {
  if (!decimalOdds || stake === 0) return 0;
  return stake * (decimalOdds - 1);
};

/**
 * Calculate profit from parlay odds (handles both American and Decimal)
 * @param {number} stake - Bet amount
 * @param {number} parlayOdds - Parlay odds (auto-detects format)
 * @returns {number} Profit amount
 */
export const calcParlayProfit = (stake, parlayOdds) => {
  if (!parlayOdds || stake === 0) return 0;

  // Detect if odds are American (>= 100 or <= -100) or Decimal
  if (parlayOdds >= 100 || parlayOdds <= -100) {
    return calcAmericanProfit(stake, parlayOdds);
  }

  // Otherwise use decimal odds logic
  return calcDecimalProfit(stake, parlayOdds);
};

/**
 * Determine overall status of a bet group
 * @param {Array} bets - Array of bet objects
 * @returns {string} Status: 'void', 'pending', 'won', or 'lost'
 */
export const getGroupStatus = (bets) => {
  if (!bets || bets.length === 0) return 'pending';

  const anyVoided = bets.some((b) => b.status === 'void');
  if (anyVoided) return 'void';

  const allPending = bets.every((b) => b.status === 'pending');
  if (allPending) return 'pending';

  const anyLost = bets.some((b) => b.status === 'lost');
  if (anyLost) return 'lost';

  const allWon = bets.every((b) => b.status === 'won');
  if (allWon) return 'won';

  return 'pending';
};

/**
 * Calculate total stake and P&L for a bet group
 * @param {Array} groupBets - Array of bets in the group
 * @returns {Object} { stake: number, pnl: number }
 */
export const computeGroupPnlAndStake = (groupBets) => {
  if (!groupBets || groupBets.length === 0) {
    return { stake: 0, pnl: 0 };
  }

  const isParlay = groupBets.length > 1 && groupBets[0].parlay_id;
  const status = getGroupStatus(groupBets);
  let stake = 0;
  let pnl = 0;

  if (status === 'void') {
    return { stake: 0, pnl: 0 };
  }

  if (isParlay) {
    // Total stake = first leg's original_stake (which equals the full parlay wager)
    // Fall back to summing stakes if original_stake not set
    stake =
      groupBets[0].original_stake || groupBets.reduce((sum, b) => sum + (b.stake || 0), 0) || 0;

    if (status === 'won') {
      // parlay_odds is the combined decimal multiplier (e.g. 1.5291 × 1.6494 = 2.5217)
      const parlayOdds = groupBets[0].parlay_odds;
      if (parlayOdds && parlayOdds > 1) {
        pnl = stake * (parlayOdds - 1);
      } else {
        // parlay_odds missing — use sum of stored leg profits (set correctly by grader)
        pnl = groupBets.reduce((sum, b) => sum + (b.profit || 0), 0);
      }
    } else if (status === 'lost') {
      pnl = -stake;
    }
  } else {
    // For singles, use stored profit (set correctly by grader with American odds)
    groupBets.forEach((b) => {
      const s = b.original_stake || b.stake || 0;
      stake += s;

      if (b.status === 'won') {
        pnl += b.profit != null ? b.profit : 0;
      } else if (b.status === 'lost') {
        pnl -= s;
      }
    });
  }

  // Safety check for infinite values
  if (!isFinite(pnl)) pnl = 0;
  if (!isFinite(stake)) stake = 0;

  return { stake, pnl };
};

/**
 * Calculate win rate from bet groups
 * @param {Array} groups - Array of bet groups
 * @returns {number} Win rate percentage (0-100)
 */
export const calculateWinRate = (groups) => {
  if (!groups || groups.length === 0) return 0;

  const finished = groups.filter((g) => ['won', 'lost'].includes(g.status));
  if (finished.length === 0) return 0;

  const wins = finished.filter((g) => g.status === 'won').length;
  return Math.round((wins / finished.length) * 100);
};

/**
 * Calculate ROI (Return on Investment)
 * @param {number} totalPnl - Total profit/loss
 * @param {number} totalStake - Total amount wagered
 * @returns {number} ROI percentage
 */
export const calculateROI = (totalPnl, totalStake) => {
  if (!totalStake || totalStake === 0) return 0;
  return Math.round((totalPnl / totalStake) * 100);
};

/**
 * Group bets by parlay_id or individual bet
 * @param {Array} bets - Array of all bets
 * @returns {Array} Array of grouped bets
 */
export const groupBetsByParlay = (bets) => {
  if (!bets || bets.length === 0) return [];

  const parlayMap = new Map();
  const singles = [];

  bets.forEach((bet) => {
    if (bet.parlay_id) {
      if (!parlayMap.has(bet.parlay_id)) {
        parlayMap.set(bet.parlay_id, []);
      }
      parlayMap.get(bet.parlay_id).push(bet);
    } else {
      singles.push([bet]);
    }
  });

  // Combine parlays and singles
  const groups = [...parlayMap.values(), ...singles];

  // Add computed properties to each group
  return groups.map((group) => {
    const { stake, pnl } = computeGroupPnlAndStake(group);
    const status = getGroupStatus(group);

    return {
      bets: group,
      status,
      stake,
      pnl,
      isParlay: group.length > 1 && group[0].parlay_id,
      parlay_id: group[0].parlay_id || null,
      placed_at: group[0].placed_at,
    };
  });
};

/**
 * Filter bet groups by status
 * @param {Array} groups - Array of bet groups
 * @param {string} status - Status to filter by
 * @returns {Array} Filtered groups
 */
export const filterGroupsByStatus = (groups, status) => {
  if (!groups || !status) return groups;
  return groups.filter((g) => g.status === status);
};

/**
 * Sort bet groups by date
 * @param {Array} groups - Array of bet groups
 * @param {string} direction - 'asc' or 'desc'
 * @returns {Array} Sorted groups
 */
export const sortGroupsByDate = (groups, direction = 'desc') => {
  if (!groups) return [];

  return [...groups].sort((a, b) => {
    const dateA = new Date(a.placed_at);
    const dateB = new Date(b.placed_at);
    return direction === 'desc' ? dateB - dateA : dateA - dateB;
  });
};
