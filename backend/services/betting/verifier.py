"""Bet verification service - re-checks all graded bets against actual game/player data"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...repositories.bet_repo import BetRepository
from ...repositories.game_repo import GameRepository
from ...repositories.player_stat_repo import PlayerStatRepository
from ...models.games_results import GameResult
from ...models.bet import Bet

logger = logging.getLogger(__name__)


class BetVerifier:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)
        self.games = GameRepository(session)
        self.stats = PlayerStatRepository(session)

    async def verify_all_graded_bets(self) -> Dict[str, Any]:
        """
        Re-check all graded bets (won/lost) against actual game results and player stats.
        Returns a list of discrepancies without modifying the database.
        """
        # Get all graded bets (won or lost, not pending or void)
        stmt = select(Bet).where(Bet.status.in_(["won", "lost"]))
        result = await self.session.execute(stmt)
        graded_bets = result.scalars().all()

        discrepancies = []
        parlays_checked = {}

        for bet in graded_bets:
            # Skip if already processed as part of a parlay
            if bet.parlay_id and bet.parlay_id in parlays_checked:
                continue

            if bet.parlay_id:
                # Verify parlay
                discrepancy = await self._verify_parlay(bet.parlay_id)
                if discrepancy:
                    discrepancies.append(discrepancy)
                    parlays_checked[bet.parlay_id] = True
            else:
                # Verify single bet
                discrepancy = await self._verify_single_bet(bet)
                if discrepancy:
                    discrepancies.append(discrepancy)

        return {
            "total_graded": len(graded_bets),
            "discrepancies_found": len(discrepancies),
            "discrepancies": discrepancies,
        }

    async def _verify_parlay(self, parlay_id: str) -> Optional[Dict[str, Any]]:
        """Verify all legs of a parlay"""
        stmt = select(Bet).where(Bet.parlay_id == parlay_id)
        result = await self.session.execute(stmt)
        legs = result.scalars().all()

        if not legs:
            return None

        leg_verifications = []
        for leg in legs:
            expected_status = await self._calculate_expected_status(leg)
            if expected_status and expected_status != leg.status:
                leg_verifications.append({
                    "bet_id": leg.id,
                    "selection": leg.selection,
                    "current_status": leg.status,
                    "expected_status": expected_status,
                    "reason": await self._get_verification_reason(leg, expected_status),
                })

        if not leg_verifications:
            # All legs are correct, now check if parlay status is correct
            all_won = all(leg.status == "won" for leg in legs)
            any_lost = any(leg.status == "lost" for leg in legs)
            
            # Parlay should be "won" only if all legs won
            # Parlay should be "lost" if any leg lost
            current_parlay_status = legs[0].status  # All legs have same status in our system
            
            if all_won and any(leg.status == "lost" for leg in legs):
                # This shouldn't happen, but catch it
                return {
                    "type": "parlay",
                    "parlay_id": parlay_id,
                    "legs": [{"bet_id": leg.id, "selection": leg.selection, "status": leg.status} for leg in legs],
                    "issue": "Inconsistent leg statuses in parlay",
                    "leg_discrepancies": [],
                }
            
            # Check if any individual leg verification is needed
            return None

        # Found discrepancies in legs
        expected_parlay_status = "lost" if any(lv["expected_status"] == "lost" for lv in leg_verifications) else "won"
        current_parlay_status = legs[0].status

        return {
            "type": "parlay",
            "parlay_id": parlay_id,
            "current_status": current_parlay_status,
            "expected_status": expected_parlay_status,
            "original_stake": legs[0].original_stake,
            "parlay_odds": legs[0].parlay_odds,
            "legs": [{"bet_id": leg.id, "selection": leg.selection, "status": leg.status} for leg in legs],
            "leg_discrepancies": leg_verifications,
        }

    async def _verify_single_bet(self, bet: Bet) -> Optional[Dict[str, Any]]:
        """Verify a single bet"""
        expected_status = await self._calculate_expected_status(bet)
        
        if not expected_status:
            return None

        if expected_status != bet.status:
            return {
                "type": "single",
                "bet_id": bet.id,
                "selection": bet.selection,
                "current_status": bet.status,
                "expected_status": expected_status,
                "current_profit": bet.profit,
                "stake": bet.stake,
                "odds": bet.odds,
                "reason": await self._get_verification_reason(bet, expected_status),
            }

        return None

    async def _calculate_expected_status(self, bet: Bet) -> Optional[str]:
        """Calculate what the bet status SHOULD be based on actual data"""
        if bet.bet_type in ("moneyline", "spread"):
            return await self._check_moneyline_result(bet)
        elif bet.bet_type == "prop":
            return await self._check_prop_result(bet)
        return None

    async def _check_moneyline_result(self, bet: Bet) -> Optional[str]:
        """Check moneyline bet against game result"""
        if not bet.game_id:
            return None

        # Try to get game result
        game = await self.games.get(bet.game_id)
        game_result = None
        
        if not game or game.home_score is None:
            stmt = select(GameResult).where(GameResult.game_id == bet.game_id)
            result = await self.session.execute(stmt)
            game_result = result.scalar_one_or_none()
            
            if not game_result or game_result.home_score is None:
                return None  # Can't verify without final score

        home_score = game.home_score if game and game.home_score is not None else (game_result.home_score if game_result else None)
        away_score = game.away_score if game and game.away_score is not None else (game_result.away_score if game_result else None)
        home_team = game.home_team_name if game else (game_result.home_team_name if game_result else None)
        away_team = game.away_team_name if game else (game_result.away_team_name if game_result else None)

        if home_score is None or away_score is None:
            return None

        # Extract team name from selection
        if not bet.selection:
            return None

        team_name = bet.selection.split()[0].lower()
        home_team_lower = (home_team or "").lower()
        away_team_lower = (away_team or "").lower()

        bet_on_home = team_name in home_team_lower or home_team_lower in team_name
        bet_on_away = team_name in away_team_lower or away_team_lower in team_name

        if not (bet_on_home or bet_on_away):
            return None

        home_won = home_score > away_score

        if bet_on_home:
            return "won" if home_won else "lost"
        else:
            return "won" if not home_won else "lost"

    async def _check_prop_result(self, bet: Bet) -> Optional[str]:
        """Check prop bet against player stats"""
        if not bet.player_id or not bet.game_id:
            return None

        stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
        if not stat:
            return None

        stat_field = bet.stat_type or bet.market
        if not stat_field:
            return None
            
        value = getattr(stat, stat_field, None)
        
        if value is None and hasattr(stat, "stats_json") and stat.stats_json:
            value = stat.stats_json.get(stat_field)

        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        # Extract line from selection
        if not bet.selection:
            return None

        import re
        numbers = re.findall(r'[-+]?\d*\.?\d+', bet.selection)
        if not numbers:
            return None

        line = float(numbers[-1])
        sel_lower = bet.selection.lower()

        if "over" in sel_lower:
            return "won" if value > line else "lost"
        else:
            return "won" if value < line else "lost"

    async def _get_verification_reason(self, bet: Bet, expected_status: str) -> str:
        """Get human-readable reason for the expected status"""
        if bet.bet_type in ("moneyline", "spread") and bet.game_id:
            game = await self.games.get(bet.game_id)
            game_result = None
            
            if not game or game.home_score is None:
                stmt = select(GameResult).where(GameResult.game_id == bet.game_id)
                result = await self.session.execute(stmt)
                game_result = result.scalar_one_or_none()

            if game and game.home_score is not None:
                return f"Final: {game.home_team_name} {game.home_score} - {game.away_score} {game.away_team_name}"
            elif game_result:
                return f"Final: {game_result.home_team_name} {game_result.home_score} - {game_result.away_score} {game_result.away_team_name}"

        elif bet.bet_type == "prop" and bet.player_id and bet.game_id:
            stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
            if stat:
                stat_field = bet.stat_type or bet.market
                if stat_field:
                    value = getattr(stat, stat_field, None)
                    if value is None and hasattr(stat, "stats_json") and stat.stats_json:
                        value = stat.stats_json.get(stat_field)
                
                if value is not None:
                    import re
                    numbers = re.findall(r'[-+]?\d*\.?\d+', bet.selection or "")
                    line = float(numbers[-1]) if numbers else 0
                    return f"Player stat: {value} (line: {line})"

        return "Verified against actual game data"

    async def apply_corrections(self, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply approved corrections to the database.
        Each correction should have 'type', 'bet_id' or 'parlay_id', and 'expected_status'.
        """
        corrected = []
        errors = []

        for correction in corrections:
            try:
                if correction["type"] == "parlay":
                    await self._correct_parlay(correction)
                    corrected.append(correction["parlay_id"])
                elif correction["type"] == "single":
                    await self._correct_single_bet(correction)
                    corrected.append(correction["bet_id"])
            except Exception as e:
                errors.append({
                    "correction": correction,
                    "error": str(e),
                })
                logger.error(f"Failed to apply correction: {e}")

        await self.session.commit()

        return {
            "corrected": len(corrected),
            "errors": len(errors),
            "corrected_ids": corrected,
            "error_details": errors,
        }

    async def _correct_parlay(self, correction: Dict[str, Any]) -> None:
        """Correct all legs of a parlay"""
        parlay_id = correction["parlay_id"]
        stmt = select(Bet).where(Bet.parlay_id == parlay_id)
        result = await self.session.execute(stmt)
        legs = list(result.scalars().all())

        # Re-grade each leg
        for leg in legs:
            expected_status = await self._calculate_expected_status(leg)
            if expected_status:
                leg.status = expected_status
                leg.graded_at = datetime.utcnow()

        # Recalculate parlay profit
        all_won = all(leg.status == "won" for leg in legs)
        original_stake = legs[0].original_stake
        parlay_odds = legs[0].parlay_odds or legs[0].odds

        if all_won:
            # Parlay wins - calculate total profit
            if parlay_odds > 0:
                total_profit = original_stake * (parlay_odds / 100)
            else:
                total_profit = original_stake / (abs(parlay_odds) / 100)
            
            profit_per_leg = total_profit / len(legs)
            for leg in legs:
                leg.profit = profit_per_leg
        else:
            # Parlay lost - distribute loss across legs
            stake_per_leg = original_stake / len(legs)
            for leg in legs:
                leg.profit = -stake_per_leg

    async def _correct_single_bet(self, correction: Dict[str, Any]) -> None:
        """Correct a single bet"""
        bet = await self.bets.get(correction["bet_id"])
        if not bet:
            raise ValueError(f"Bet {correction['bet_id']} not found")

        expected_status = await self._calculate_expected_status(bet)
        if expected_status:
            bet.status = expected_status
            bet.graded_at = datetime.utcnow()
            
            # Recalculate profit
            stake = bet.stake
            odds = bet.odds

            if expected_status == "won":
                if odds > 0:
                    bet.profit = stake * (odds / 100)
                else:
                    bet.profit = stake / (abs(odds) / 100)
            else:
                bet.profit = -stake
