"""Bet verification service - re-checks all graded bets against actual game/player data"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from sqlalchemy import select
from ...models.games_results import GameResult
from ...models.bet import Bet

logger = logging.getLogger(__name__)


class BetVerifier:
    def __init__(self, session):
        self.session = session
        from ...repositories.bet_repo import BetRepository
        from ...repositories.game_repo import GameRepository
        from ...repositories.player_stat_repo import PlayerStatRepository
        from ...repositories.injury_repo import InjuryRepository  # Add this import

        self.bets = BetRepository(session)
        self.games = GameRepository(session)
        self.stats = PlayerStatRepository(session)
        self.injuries = InjuryRepository(session)  # Initialize injuries repository

    async def _verify_single_bet(self, bet: Bet) -> Optional[Dict[str, Any]]:
        """Verify a single bet and return discrepancy if found."""
        current_status = bet.status or ""
        expected_status = await self._calculate_expected_status(bet)
        if expected_status is None:
            return None

        # For prop bets missing a result value, void them immediately
        if bet.bet_type in ("prop", "total") and bet.result_value is None:
            bet.status = "void"
            bet.profit = 0
            bet.graded_at = datetime.utcnow()
            await self.session.flush()
            return {
                "type": "single",
                "bet_id": bet.id,
                "selection": bet.selection or "",
                "current_status": current_status,
                "expected_status": "void",
                "current_profit": bet.profit,
                "stake": bet.stake,
                "odds": bet.odds,
                "reason": "Missing stat value for grading",
            }

        profit = None
        if expected_status == "won":
            odds = bet.odds
            stake = bet.stake
            # Handle both decimal odds (1.01-99) and American odds
            if 1.01 <= odds < 100:
                profit = round(stake * (odds - 1), 2)
            elif odds > 0:
                profit = round(stake * (odds / 100), 2)
            else:
                profit = round(stake * (100 / abs(odds)), 2)
        elif expected_status == "lost":
            profit = -bet.stake
        elif expected_status == "push":
            profit = 0

        if expected_status == current_status:
            return None

        # Status mismatch — correct it
        bet.status = expected_status
        bet.profit = profit
        bet.graded_at = datetime.utcnow()
        await self.session.flush()
        return {
            "type": "single",
            "bet_id": bet.id,
            "selection": bet.selection or "",
            "current_status": current_status,
            "expected_status": expected_status,
            "current_profit": bet.profit,
            "stake": bet.stake,
            "odds": bet.odds,
            "reason": await self._get_verification_reason(bet, str(expected_status)),
        }

    async def verify_all_graded_bets(self) -> Dict[str, Any]:
        """
        Re-check all graded bets (won/lost) against actual game/player data.
        Returns a list of discrepancies without modifying the database.
        """
        # Get all bets that are graded or voided (not pending)
        stmt = select(Bet).where(Bet.status.in_(["won", "lost", "void"]))
        result = await self.session.execute(stmt)
        graded_bets = result.scalars().all()

        discrepancies = []
        parlays_checked = {}

        for bet in graded_bets:
            # Skip if already processed as part of a parlay
            if bet.parlay_id and bet.parlay_id in parlays_checked:
                continue

            if bet.parlay_id:
                # Verify parlay using unified logic
                discrepancy = await self._verify_parlay(bet.parlay_id)
                if discrepancy:
                    discrepancies.append(discrepancy)
                parlays_checked[bet.parlay_id] = True
            else:
                # Verify single bet
                discrepancy = await self._verify_single_bet(bet)
                if discrepancy:
                    discrepancies.append(discrepancy)

        logger.info(
            f"Verification complete: {len(graded_bets)} graded bets, {len(discrepancies)} discrepancies found."
        )
        for d in discrepancies:
            logger.info(f"Discrepancy: {d}")
        return {
            "total_graded": len(graded_bets),
            "discrepancies_found": len(discrepancies),
            "discrepancies": discrepancies,
        }

    async def _verify_parlay(self, parlay_id: str) -> Optional[Dict[str, Any]]:
        """Verify all legs of a parlay and recalculate profit using unified logic"""
        stmt = select(Bet).where(Bet.parlay_id == parlay_id)
        result = await self.session.execute(stmt)
        legs = result.scalars().all()
        if not legs:
            return None

        expected_statuses = []
        leg_verifications = []
        for leg in legs:
            expected_status = await self._calculate_expected_status(leg)
            expected_statuses.append(expected_status)
            if expected_status and expected_status != leg.status:
                # Correct the leg status and profit
                leg.status = expected_status
                if expected_status == "won":
                    leg.profit = leg.stake * (leg.odds - 1)
                elif expected_status == "lost":
                    leg.profit = -leg.stake
                else:
                    leg.profit = 0
                leg.graded_at = datetime.utcnow()
                await self.session.flush()
                leg_verifications.append(
                    {
                        "bet_id": leg.id,
                        "selection": leg.selection,
                        "current_status": leg.status,
                        "expected_status": expected_status,
                        "reason": await self._get_verification_reason(
                            leg, expected_status
                        ),
                    }
                )

        # If any leg is void, parlay is void and not counted in P/L
        any_void = any(s == "void" for s in expected_statuses)
        any_lost = any(s == "lost" for s in expected_statuses)
        all_won = all(s == "won" for s in expected_statuses)

        if any_void:
            expected_parlay_status = "void"
        elif any_lost:
            expected_parlay_status = "lost"
        elif all_won:
            expected_parlay_status = "won"
        else:
            expected_parlay_status = "void"

        # Use synthetic parlay status (not DB field)
        current_parlay_status = (
            "void"
            if any(leg.status == "void" for leg in legs)
            else (
                "lost"
                if any(leg.status == "lost" for leg in legs)
                else ("won" if all(leg.status == "won" for leg in legs) else "void")
            )
        )

        if not leg_verifications and current_parlay_status == expected_parlay_status:
            return None

        original_stake = legs[0].original_stake
        parlay_odds = legs[0].parlay_odds or legs[0].odds
        return {
            "type": "parlay",
            "parlay_id": parlay_id,
            "current_status": current_parlay_status,
            "expected_status": expected_parlay_status,
            "original_stake": original_stake,
            "parlay_odds": parlay_odds,
            "legs": [
                {
                    "bet_id": leg.id,
                    "selection": leg.selection,
                    "status": leg.status,
                    "profit": leg.profit,
                }
                for leg in legs
            ],
            "leg_discrepancies": leg_verifications,
        }

        # Remove undefined 'bet' block left over from previous patch

    async def _calculate_expected_status(self, bet: Bet) -> Optional[str]:
        """Calculate what the bet status SHOULD be based on actual data"""
        # Allow regrading void bets if game/player data is available
        if bet.bet_type in ("moneyline", "spread"):
            # If bet is void but game result is available, regrade
            if bet.status == "void":
                result = await self._check_moneyline_result(bet)
                if result is not None:
                    return result
            else:
                return await self._check_moneyline_result(bet)
        elif bet.bet_type in ("prop", "total"):
            # If bet is void but game/player data is available, regrade
            if bet.status == "void":
                result = await self._check_prop_result(bet)
                if result is not None:
                    return result
            else:
                return await self._check_prop_result(bet)
        return None

    async def _check_moneyline_result(self, bet: Bet) -> Optional[str]:
        """Check moneyline or spread bet against game result"""
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

        home_score = (
            game.home_score
            if game and game.home_score is not None
            else (game_result.home_score if game_result else None)
        )
        away_score = (
            game.away_score
            if game and game.away_score is not None
            else (game_result.away_score if game_result else None)
        )
        home_team = (
            game.home_team_name
            if game
            else (game_result.home_team_name if game_result else None)
        )
        away_team = (
            game.away_team_name
            if game
            else (game_result.away_team_name if game_result else None)
        )

        if home_score is None or away_score is None:
            return None

        # Extract team name from selection (strip trailing bet-type keywords)
        if not bet.selection:
            return None

        _STOP_WORDS = {"ml", "moneyline", "spread", "total", "over", "under", "pk"}
        parts = bet.selection.split()
        team_words = []
        for part in parts:
            if part.lower() in _STOP_WORDS:
                break
            if re.match(r"^[+\-ouOU]?\d", part):
                break
            team_words.append(part)
        team_name = (" ".join(team_words) if team_words else parts[0]).lower()

        home_team_lower = (home_team or "").lower()
        away_team_lower = (away_team or "").lower()

        bet_on_home = team_name in home_team_lower or home_team_lower in team_name
        bet_on_away = team_name in away_team_lower or away_team_lower in team_name

        if not (bet_on_home or bet_on_away):
            return None

        # Handle spread bets
        if bet.bet_type == "spread":
            spread_line = 0.0
            # Extract spread line from selection (last numeric token with optional sign)
            sel_parts = bet.selection.split()
            for part in reversed(sel_parts):
                m = re.match(r"^([+\-]?\d+\.?\d*)$", part)
                if m:
                    spread_line = float(m.group(1))
                    break

            if bet_on_home:
                adjusted = home_score + spread_line
                if adjusted > away_score:
                    return "won"
                elif adjusted == away_score:
                    return "push"
                else:
                    return "lost"
            else:
                adjusted = away_score + spread_line
                if adjusted > home_score:
                    return "won"
                elif adjusted == home_score:
                    return "push"
                else:
                    return "lost"

        # Handle moneyline bets (who won outright)
        home_won = home_score > away_score

        if bet_on_home:
            return "won" if home_won else "lost"
        else:
            return "won" if not home_won else "lost"

    async def _check_prop_result(self, bet: Bet) -> Optional[str]:
        """Check prop bet against player stats, auto-void if injured or DNP."""
        if not bet.game_id:
            return None

        sel_lower = (bet.selection or "").lower()
        is_totals = (not bet.player_id) and (
            "over" in sel_lower
            or "under" in sel_lower
            or (bet.stat_type and bet.stat_type.lower() == "total")
        )

        # Totals bet: use game scores if player stats are missing
        if is_totals:
            game = await self.games.get(bet.game_id)
            game_result = None
            if not game or game.home_score is None:
                stmt = select(GameResult).where(GameResult.game_id == bet.game_id)
                result = await self.session.execute(stmt)
                game_result = result.scalar_one_or_none()
            home_score = (
                game.home_score
                if game and game.home_score is not None
                else (game_result.home_score if game_result else None)
            )
            away_score = (
                game.away_score
                if game and game.away_score is not None
                else (game_result.away_score if game_result else None)
            )
            if home_score is not None and away_score is not None:
                value = home_score + away_score
                selection_str = bet.selection or ""
                numbers = re.findall(r"[-+]?\d*\.?\d+", selection_str)
                if not numbers:
                    return None
                line = float(numbers[-1])
                if "over" in sel_lower:
                    return "won" if value > line else "lost"
                else:
                    return "won" if value < line else "lost"

        # Fallback: original player stat grading
        if not bet.player_id:
            return None
        stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
        if not stat:
            return None
        # Auto-void if minutes is None/0/NaN
        minutes = getattr(stat, "minutes", None)
        try:
            min_val = float(minutes) if minutes is not None else None
        except (TypeError, ValueError):
            min_val = None
        if min_val is None or min_val == 0:
            return "void"
        # Optionally, check injuries table for player_id/game_id and status == 'Out'
        # (Assume self.injuries is available, otherwise skip)
        if hasattr(self, "injuries"):
            injury = await self.injuries.get_for_player_game(bet.player_id, bet.game_id)
            if injury and getattr(injury, "status", "").lower() == "out":
                return "void"
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
        if not bet.selection:
            return None
        selection_str = bet.selection or ""
        numbers = re.findall(r"[-+]?\d*\.?\d+", selection_str)
        if not numbers:
            return None
        line = float(numbers[-1])
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

        elif bet.bet_type in ("prop", "total") and bet.player_id and bet.game_id:
            stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
            if stat:
                # Check DNP
                minutes = getattr(stat, "minutes", None)
                try:
                    min_val = float(minutes) if minutes is not None else None
                except (TypeError, ValueError):
                    min_val = None
                if min_val is None or min_val == 0:
                    return "Final: Player did not play (DNP) - bet voided"

                stat_field = bet.stat_type or bet.market
                if stat_field:
                    # Use same alias resolution as grader
                    _FIELD_ALIASES = {
                        "pts": "points",
                        "points": "points",
                        "reb": "rebounds",
                        "rebounds": "rebounds",
                        "trb": "rebounds",
                        "ast": "assists",
                        "assists": "assists",
                        "stl": "steals",
                        "steals": "steals",
                        "blk": "blocks",
                        "blocks": "blocks",
                        "pra": None,
                    }
                    mapped = _FIELD_ALIASES.get(
                        stat_field.lower().strip(), stat_field.lower().strip()
                    )
                    if stat_field.lower().strip() == "pra":
                        p = getattr(stat, "points", None) or 0
                        r = getattr(stat, "rebounds", None) or 0
                        a = getattr(stat, "assists", None) or 0
                        value = float(p + r + a) if any([p, r, a]) else None
                    elif mapped:
                        value = getattr(stat, mapped, None)
                        if (
                            value is None
                            and hasattr(stat, "stats_json")
                            and stat.stats_json
                        ):
                            value = stat.stats_json.get(mapped) or stat.stats_json.get(
                                stat_field
                            )
                    else:
                        value = None

                    if value is not None:
                        numbers = re.findall(r"[-+]?\d*\.?\d+", bet.selection or "")
                        line = float(numbers[-1]) if numbers else 0
                        player_name = bet.player_name or "Player"
                        return (
                            f"Final: {player_name} {stat_field}: {value} (line: {line})"
                        )

        return "Verified against actual game data"

    async def apply_corrections(
        self, corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply approved corrections to the database.
        Each correction should have 'type', 'bet_id' or 'parlay_id', and 'expected_status'.
        """
        corrected = []
        errors = []

        for correction in corrections:
            try:
                logger.info(f"Applying correction: {correction}")
                if correction["type"] == "parlay":
                    await self._correct_parlay(correction)
                    corrected.append(correction["parlay_id"])
                elif correction["type"] == "single":
                    await self._correct_single_bet(correction)
                    corrected.append(correction["bet_id"])
            except Exception as e:
                errors.append(
                    {
                        "correction": correction,
                        "error": str(e),
                    }
                )
                logger.error(f"Failed to apply correction: {e}")

        await self.session.commit()
        logger.info(f"Corrections committed. Corrected IDs: {corrected}")

        # Post-correction verification
        for correction in corrections:
            if correction["type"] == "single":
                bet = await self.bets.get(correction["bet_id"])
                if bet:
                    logger.info(
                        f"Post-correction bet {bet.id}: status={bet.status}, profit={bet.profit}"
                    )
                else:
                    logger.warning(
                        f"Post-correction bet {correction['bet_id']} not found."
                    )
            elif correction["type"] == "parlay":
                stmt = select(Bet).where(Bet.parlay_id == correction["parlay_id"])
                result = await self.session.execute(stmt)
                legs = result.scalars().all()
                for leg in legs:
                    logger.info(
                        f"Post-correction parlay leg {leg.id}: status={leg.status}, profit={leg.profit}"
                    )

        # Immediately re-run verification to check for remaining discrepancies
        logger.info("Re-running verification after corrections...")
        verify_result = await self.verify_all_graded_bets()
        logger.info(
            f"Post-correction verification: {verify_result['discrepancies_found']} discrepancies found."
        )
        for d in verify_result["discrepancies"]:
            logger.info(f"Post-correction discrepancy: {d}")

        return {
            "corrected": len(corrected),
            "errors": len(errors),
            "corrected_ids": corrected,
            "error_details": errors,
            "post_correction_verification": verify_result,
        }

    async def _correct_parlay(self, correction: Dict[str, Any]) -> None:
        """Correct all legs of a parlay."""
        parlay_id = correction["parlay_id"]
        stmt = select(Bet).where(Bet.parlay_id == parlay_id)
        result = await self.session.execute(stmt)
        legs = list(result.scalars().all())

        logger.debug(
            "Parlay %s leg statuses BEFORE: %s", parlay_id, [leg.status for leg in legs]
        )

        # Re-grade each leg
        for leg in legs:
            expected_status = await self._calculate_expected_status(leg)
            if expected_status:
                logger.info(
                    "Updating parlay leg %s: status=%s", leg.id, expected_status
                )
                leg.status = expected_status
                leg.graded_at = datetime.utcnow()
        await self.session.flush()
        logger.debug("Parlay %s legs updated and flushed.", parlay_id)

        expected_status = correction.get("expected_status")
        original_stake = legs[0].original_stake
        if expected_status == "void":
            for leg in legs:
                leg.status = "void"
                leg.profit = 0.0
                logger.info("Parlay leg %s set to void (correction override).", leg.id)
            parlay_status = "void"
        else:
            active_legs = [leg for leg in legs if leg.status not in ("void", "push")]
            void_legs = [leg for leg in legs if leg.status in ("void", "push")]
            all_won = all(
                leg.status in ("won", "void", "push") for leg in legs
            ) and any(leg.status == "won" for leg in legs)
            any_lost = any(leg.status == "lost" for leg in legs)
            if any_lost:
                stake_per_leg = original_stake / len(legs)
                for leg in legs:
                    leg.status = "lost"
                    leg.profit = -stake_per_leg
                    logger.info(
                        "Parlay leg %s set to lost, profit=%s.", leg.id, -stake_per_leg
                    )
                parlay_status = "lost"
            elif all_won:
                if active_legs:
                    combined_odds = 1.0
                    for leg in active_legs:
                        combined_odds *= leg.odds
                    total_profit = original_stake * (combined_odds - 1)
                    profit_per_leg = total_profit / len(active_legs)
                    for leg in active_legs:
                        leg.status = "won"
                        leg.profit = profit_per_leg
                        logger.info(
                            "Parlay leg %s set to won, profit=%s.",
                            leg.id,
                            profit_per_leg,
                        )
                    for leg in void_legs:
                        leg.status = "void"
                        leg.profit = 0.0
                else:
                    for leg in legs:
                        leg.status = "void"
                        leg.profit = 0.0
                parlay_status = "won"
            else:
                for leg in legs:
                    leg.status = "void"
                    leg.profit = 0.0
                    logger.info("Parlay leg %s set to void (parlay void).", leg.id)
                parlay_status = "void"

        await self.session.flush()
        logger.debug(
            "Parlay %s leg statuses AFTER: %s", parlay_id, [leg.status for leg in legs]
        )
        logger.info("Parlay %s resolved to %s, committing.", parlay_id, parlay_status)
        await self.session.commit()

    async def _correct_single_bet(self, correction: Dict[str, Any]) -> None:
        """Correct a single bet"""
        bet = await self.bets.get(correction["bet_id"])
        if not bet:
            raise ValueError(f"Bet {correction['bet_id']} not found")

        expected_status = await self._calculate_expected_status(bet)
        if expected_status:
            logger.info(f"Updating bet {bet.id}: status={expected_status}")
            bet.status = expected_status
            bet.graded_at = datetime.utcnow()
            # Always use decimal odds for profit calculation
            stake = bet.stake
            odds = bet.odds
            if expected_status == "won":
                bet.profit = (stake * odds) - stake
                logger.info(f"Bet {bet.id} profit set to {bet.profit}")
            else:
                bet.profit = -stake
                logger.info(f"Bet {bet.id} profit set to {-stake}")
            await self.session.flush()
            logger.info(f"Bet {bet.id} updated and flushed.")
