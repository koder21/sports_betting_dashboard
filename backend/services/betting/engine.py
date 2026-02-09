from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .parser import BetParser
from .grader import BetGrader
from ...repositories.bet_repo import BetRepository
from ...repositories.game_repo import GameRepository
from ...repositories.player_repo import PlayerRepository
from ...services.alerts.manager import AlertManager
from ...models.games_results import GameResult


class BettingEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)
        self.games = GameRepository(session)
        self.players = PlayerRepository(session)
        self.parser = BetParser(session)
        self.grader = BetGrader(session)

    async def place_bets_from_text(self, raw_text: str) -> Dict[str, Any]:
        """Parse and place multiple bets from text format"""
        parsed_bets = await self.parser.parse_multiple(raw_text)
        if not parsed_bets:
            return {"status": "error", "message": "Unable to parse bets"}

        from ...models.bet import Bet

        # Validate that all bets have valid game IDs (moneyline/spread) or player IDs (props)
        invalid_bets = []
        for bet_data in parsed_bets:
            bet_type = bet_data.get("bet_type", "").lower()
            game_id = bet_data.get("game_id")
            player_id = bet_data.get("player_id")
            selection = bet_data.get("selection", "")
            sport_id = bet_data.get("sport_id")
            
            # Moneyline and spread bets MUST have a game_id AND it must exist in the database
            if bet_type in ["moneyline", "spread"]:
                if not game_id:
                    invalid_bets.append({
                        "selection": selection,
                        "reason": f"Could not find game matching '{bet_data.get('game_str', 'unknown')}' on the date specified"
                    })
                else:
                    # Check if game actually exists in the database (don't require sport_id match)
                    game = await self.games.get_by_espn(str(game_id))
                    if not game:
                        invalid_bets.append({
                            "selection": selection,
                            "reason": f"Game ID {game_id} not found in database. Game may not have been scraped yet."
                        })
            # Prop bets should have either player_id or player_name
            elif bet_type == "prop":
                if not player_id and not bet_data.get("player_name"):
                    invalid_bets.append({
                        "selection": selection,
                        "reason": "Could not identify player for this prop bet"
                    })
        
        if invalid_bets:
            return {
                "status": "error",
                "message": "Could not match the following bets to real games/players",
                "invalid_bets": invalid_bets
            }

        created_bets = []
        parlay_ids = {}
        parlay_legs = {}  # Track legs for each parlay to calculate odds
        
        # First pass: group bets by parlay and count legs
        parlay_groups = {}
        for bet_data in parsed_bets:
            parlay_name = bet_data.get('parlay_name', 'Single')
            if parlay_name not in parlay_groups:
                parlay_groups[parlay_name] = []
            parlay_groups[parlay_name].append(bet_data)
        
        # Second pass: create bets with divided stakes for parlays
        for parlay_name, group_bets in parlay_groups.items():
            parlay_id = str(uuid.uuid4())
            parlay_ids[parlay_name] = parlay_id
            
            # For parlays with multiple legs, divide stake equally
            is_parlay = len(group_bets) > 1
            
            for bet_data in group_bets:
                # Get the original stake value
                original_stake = bet_data.get("stake", 100)
                
                # Divide stake by number of legs if it's a parlay
                if is_parlay:
                    stake = original_stake / len(group_bets)
                else:
                    stake = original_stake
                
                odds = bet_data.get("odds", -110)
                parlay_legs.setdefault(parlay_name, []).append(odds)
                
                bet = Bet(
                    placed_at=datetime.utcnow(),
                    sport_id=bet_data["sport_id"],
                    game_id=bet_data.get("game_id"),
                    player_id=bet_data.get("player_id"),
                    parlay_id=parlay_id,
                    raw_text=bet_data.get("raw_text", raw_text),
                    original_stake=original_stake,
                    stake=stake,
                    odds=odds,
                    bet_type=bet_data.get("bet_type"),
                    market=bet_data.get("market"),
                    selection=bet_data.get("selection"),
                    stat_type=bet_data.get("stat_type"),
                    player_name=bet_data.get("player_name"),
                    reason=bet_data.get("reason"),
                    status="pending",
                )

                await self.bets.add(bet)
                created_bets.append({
                    "id": bet.id,
                    "selection": bet.selection,
                    "odds": bet.odds,
                    "stake": stake,
                    "game_id": bet.game_id,
                    "parlay_id": bet.parlay_id
                })

        await self.session.commit()
        
        # Calculate and update parlay odds
        for parlay_name, leg_odds in parlay_legs.items():
            if len(leg_odds) > 1:  # Only calculate for actual parlays
                parlay_odds = self._calculate_parlay_odds(leg_odds)
                parlay_id = parlay_ids[parlay_name]
                
                # Update all bets in this parlay with the calculated odds
                await self.bets.update_parlay_odds(parlay_id, parlay_odds)

        await self.session.commit()

        return {
            "status": "ok",
            "bets_created": len(created_bets),
            "bets": created_bets
        }

    async def place_bet(self, raw_text: str, stake: float, odds: float) -> Dict[str, Any]:
        """Legacy single-bet placement"""
        parsed = await self.parser.parse(raw_text)
        if not parsed:
            return {"status": "error", "message": "Unable to parse bet text"}

        from ...models.bet import Bet

        bet = Bet(
            placed_at=datetime.utcnow(),
            sport_id=parsed["sport_id"],
            game_id=parsed.get("game_id"),
            player_id=parsed.get("player_id"),
            raw_text=raw_text,
            stake=stake,
            odds=odds,
            bet_type=parsed["bet_type"],
            market=parsed.get("market"),
            selection=parsed.get("selection"),
            status="pending",
        )

        await self.bets.add(bet)
        await self.session.commit()

        return {"status": "ok", "bet_id": bet.id}

    async def get_bets_with_details(self) -> List[Dict[str, Any]]:
        """Get all bets with game and player details"""
        all_bets = await self.bets.list_all_with_relations()
        
        result = []
        for bet in all_bets:
            bet_detail = {
                "id": bet.id,
                "placed_at": bet.placed_at.isoformat() if bet.placed_at else None,
                "bet_type": bet.bet_type,
                "game_id": bet.game_id,
                "selection": bet.selection,
                "player_name": bet.player_name,
                "stake": bet.stake,
                "original_stake": bet.original_stake,
                "odds": bet.odds,
                "parlay_odds": bet.parlay_odds,
                "status": bet.status,
                "profit": bet.profit,
                "result_value": bet.result_value,
                "reason": bet.reason,
                "parlay_id": bet.parlay_id,
                "game": None,
                "player": None
            }
            
            # Add game details
            if bet.game_id and bet.game:
                game = bet.game
                
                # Try to get scores from games_results if not in games table
                home_score = game.home_score
                away_score = game.away_score
                status = game.status
                
                # If scores are missing or 0, check the result relationship
                if (home_score is None or home_score == 0) and hasattr(game, 'result') and game.result:
                    home_score = game.result.home_score
                    away_score = game.result.away_score
                    if game.result.status:
                        status = game.result.status
                
                bet_detail["game"] = {
                    "game_id": game.game_id,
                    "home_team": game.home_team_name,
                    "away_team": game.away_team_name,
                    "scheduled_at": game.start_time.isoformat() if game.start_time else None,
                    "status": status,
                    "home_score": home_score,
                    "away_score": away_score,
                    "venue": game.venue
                }
            
            # Add player details
            if bet.player_id and bet.player:
                player = bet.player
                player_name = player.full_name or player.name
                # Safely access team - it may be None if foreign key is broken
                team_name = None
                try:
                    if player.team:
                        team_name = player.team.name
                except Exception as e:
                    # Log but don't crash if team relationship fails
                    import logging
                    logging.warning(f"Failed to load team for player {player.player_id}: {e}")
                
                bet_detail["player"] = {
                    "player_id": player.player_id,
                    "name": player_name,
                    "team": team_name,
                    "position": player.position
                }
            
            result.append(bet_detail)
        
        return result

    async def grade_all_pending(self) -> Dict[str, Any]:
        pending = await self.bets.list_pending()
        results = []
        parlays_to_check = {}
        parlays_touched = set()

        # Grade individual legs
        for bet in pending:
            graded = await self.grader.grade(bet)
            if graded:
                results.append(graded)
                # Track parlay legs for profit recalculation
                if bet.parlay_id:
                    if bet.parlay_id not in parlays_to_check:
                        parlays_to_check[bet.parlay_id] = []
                    parlays_to_check[bet.parlay_id].append(bet)
                    parlays_touched.add(bet.parlay_id)

        # Recalculate parlay profits based on all legs
        for parlay_id, legs in parlays_to_check.items():
            # Skip if not all legs are graded
            if any(leg.status == "pending" for leg in legs):
                continue
                
            # Check if all legs won
            all_won = all(leg.status == "won" for leg in legs)
            
            # Get original stake and parlay odds from first leg
            original_stake = legs[0].original_stake
            parlay_odds = legs[0].parlay_odds or legs[0].odds
            
            if all_won:
                # Calculate parlay win profit
                if parlay_odds > 0:
                    total_profit = original_stake * (parlay_odds / 100)
                else:
                    total_profit = original_stake / (abs(parlay_odds) / 100)
                
                # Distribute profit equally across legs
                profit_per_leg = total_profit / len(legs)
                for leg in legs:
                    leg.profit = profit_per_leg
            else:
                # Parlay lost - all legs lose their stake
                stake_per_leg = original_stake / len(legs)
                for leg in legs:
                    leg.profit = -stake_per_leg

        alerts = AlertManager(session=self.session)

        # Alerts for single bets
        for bet in pending:
            if bet.parlay_id:
                continue
            if bet.status not in ("won", "lost"):
                continue

            message = await self._build_single_alert_message(bet)
            severity = "info" if bet.status == "won" else "warning"
            
            # Get game info for context
            game_info = None
            if bet.game_id:
                game = await self.games.get(bet.game_id)
                if game:
                    game_info = f"{game.home_team_name} vs {game.away_team_name}"
            
            metadata = json.dumps({
                "bet_id": bet.id,
                "status": bet.status,
                "selection": bet.selection,
                "odds": bet.odds,
                "stake": bet.stake,
                "profit": bet.profit,
                "bet_type": bet.bet_type,
                "sport": bet.sport.name if bet.sport else None,
                "game_info": game_info,
            })
            await alerts.create(
                severity=severity,
                category="bet_graded",
                message=message,
                metadata=metadata,
            )

        # Alerts for parlays (only when all legs are graded)
        for parlay_id in parlays_touched:
            legs = await self._get_parlay_legs(parlay_id)
            if not legs:
                continue
            if any(leg.status == "pending" for leg in legs):
                continue

            if all(leg.status == "won" for leg in legs):
                parlay_status = "won"
            elif any(leg.status == "lost" for leg in legs):
                parlay_status = "lost"
            else:
                continue

            message = await self._build_parlay_alert_message(parlay_id, legs, parlay_status)
            severity = "info" if parlay_status == "won" else "warning"
            
            # Calculate total profit for the parlay
            total_profit = sum(leg.profit for leg in legs if leg.profit)
            
            metadata = json.dumps({
                "parlay_id": parlay_id,
                "status": parlay_status,
                "leg_count": len(legs),
                "selection": f"{len(legs)}-Leg Parlay",
                "odds": legs[0].parlay_odds if legs else 0,
                "stake": legs[0].original_stake if legs else 0,
                "profit": total_profit,
                "bet_type": "parlay",
                "sport": legs[0].sport.name if legs and legs[0].sport else None,
                "legs": [{"selection": leg.selection, "status": leg.status} for leg in legs],
            })
            await alerts.create(
                severity=severity,
                category="bet_graded",
                message=message,
                metadata=metadata,
            )

        # Clean up ESPN client
        await self.grader.close()
        
        await self.session.commit()
        return {"status": "ok", "graded": results}

    async def _get_parlay_legs(self, parlay_id: str):
        stmt = select(self.bets.model).where(self.bets.model.parlay_id == parlay_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _extract_line_value(self, selection: Optional[str]) -> Optional[float]:
        if not selection:
            return None
        numbers = re.findall(r"[-+]?\d*\.?\d+", selection)
        if not numbers:
            return None
        try:
            return float(numbers[-1])
        except ValueError:
            return None

    async def _get_game_score_line(self, bet) -> Optional[str]:
        if not bet.game_id:
            return None

        game = await self.games.get(bet.game_id)
        if game and game.home_score is not None and game.away_score is not None:
            return f"{game.home_team_name} {game.home_score} - {game.away_score} {game.away_team_name}"

        stmt = select(GameResult).where(GameResult.game_id == bet.game_id)
        result = await self.session.execute(stmt)
        game_result = result.scalar_one_or_none()
        if game_result and game_result.home_score is not None and game_result.away_score is not None:
            return f"{game_result.home_team_name} {game_result.home_score} - {game_result.away_score} {game_result.away_team_name}"

        return None

    async def _build_single_alert_message(self, bet) -> str:
        bet_label = bet.selection or bet.player_name or f"Bet #{bet.id}"
        status_label = bet.status.upper()

        detail = await self._build_bet_detail(bet)
        if detail:
            return f"Single bet {status_label}: {bet_label}\n{detail}"

        return f"Single bet {status_label}: {bet_label}"

    async def _build_parlay_alert_message(self, parlay_id: str, legs: List[Any], status: str) -> str:
        stake = legs[0].original_stake if legs else 0
        parlay_odds = legs[0].parlay_odds or legs[0].odds if legs else 0
        odds_label = f"{parlay_odds:+.0f}" if parlay_odds else "N/A"

        header = (
            f"Parlay {status.upper()} ({len(legs)} legs, odds {odds_label}, "
            f"stake ${stake:.2f})"
        )

        lines = []
        for leg in legs:
            leg_label = leg.selection or leg.player_name or f"Leg #{leg.id}"
            detail = await self._build_bet_detail(leg)
            if detail:
                lines.append(f"- {leg_label}: {detail} [{leg.status.upper()}]")
            else:
                lines.append(f"- {leg_label} [{leg.status.upper()}]")

        if lines:
            return f"{header}\n" + "\n".join(lines)

        return header

    async def _build_bet_detail(self, bet) -> Optional[str]:
        if bet.bet_type in ("moneyline", "spread"):
            score_line = await self._get_game_score_line(bet)
            if score_line:
                return f"Final score: {score_line}"
            return None

        if bet.bet_type == "prop":
            stat_label = bet.stat_type or bet.market or "stat"
            line = self._extract_line_value(bet.selection)
            if bet.result_value is not None and line is not None:
                return f"Result: {stat_label} {bet.result_value} vs {line}"
            if bet.result_value is not None:
                return f"Result: {stat_label} {bet.result_value}"
            return None

        return None

    def _calculate_parlay_odds(self, leg_odds_list: List[float]) -> float:
        """Calculate true parlay odds from individual leg odds"""
        decimal_odds = []
        
        for odds in leg_odds_list:
            if odds > 0:
                # Positive odds: decimal = (odds / 100) + 1
                decimal = (odds / 100) + 1
            else:
                # Negative odds: decimal = (100 / abs(odds)) + 1
                decimal = (100 / abs(odds)) + 1
            decimal_odds.append(decimal)
        
        # Multiply all decimal odds
        parlay_decimal = 1.0
        for decimal in decimal_odds:
            parlay_decimal *= decimal
        
        # Convert back to American odds
        parlay_american = (parlay_decimal - 1) * 100
        
        # Return as integer
        return int(round(parlay_american))