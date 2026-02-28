import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...repositories.player_stat_repo import PlayerStatRepository
from ...repositories.game_repo import GameRepository
from ...models.games_results import GameResult
from ..espn_client import ESPNClient

logger = logging.getLogger(__name__)


class BetGrader:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats = PlayerStatRepository(session)
        self.games = GameRepository(session)
        self._espn_client = None

    @property
    def espn_client(self):
        """Lazy-load ESPN client."""
        if self._espn_client is None:
            self._espn_client = ESPNClient()
        return self._espn_client

    async def close(self):
        """Proper cleanup of ESPN client session."""
        if self._espn_client and hasattr(self._espn_client, '_session') and self._espn_client._session:
            if not self._espn_client._session.closed:
                await self._espn_client.close()

    async def grade(self, bet) -> Optional[Dict[str, Any]]:
        #logger.debug(f"[Grader] Grading bet {bet.id}: type={bet.bet_type}, selection={bet.selection}, status={bet.status}, game_id={bet.game_id}, player_id={getattr(bet, 'player_id', None)}")
        if bet.bet_type in ("prop", "total"):
            result = await self._grade_prop(bet)
            if not result:
                logger.debug(f"[Grader] Bet {bet.id} not graded: _grade_prop returned None")
            else:
                logger.debug(f"[Grader] Bet {bet.id} graded: {result}")
            return result

        if bet.bet_type in ("moneyline", "spread"):
            result = await self._grade_game(bet)
            #if not result:
            #    logger.debug(f"[Grader] Bet {bet.id} not graded: _grade_game returned None")
            #else:
            #    logger.debug(f"[Grader] Bet {bet.id} graded: {result}")
            return result

        #logger.debug(f"[Grader] Bet {bet.id} not graded: unknown bet_type {bet.bet_type}")
        return None

    async def _grade_prop(self, bet) -> Optional[Dict[str, Any]]:
        if not bet.game_id:
            logger.warning(f"[Grader] Skipping bet {bet.id}: missing game_id (game_id={bet.game_id})")
            return None

        try:
            game = await self.games.get(bet.game_id)
            if not game or not self._is_final_status(game.status):
                #logger.info(f"[Grader] Bet {bet.id}: game not final or not found (game_id={bet.game_id}, status={getattr(game, 'status', None)})")
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    #logger.info(f"[Grader] Bet {bet.id}: game_result not final or not found (game_id={bet.game_id}, status={getattr(game_result, 'status', None)})")
                    return None
                if game and game_result:
                    game.home_score = game_result.home_score
                    game.away_score = game_result.away_score
                    game.status = game_result.status
                    await self.session.flush()

            # Totals bet logic: if stat_type is 'total' or selection contains 'over'/'under', use game scores
            sel = (bet.selection or "").strip().lower()
            is_totals = 'over' in sel or 'under' in sel or (bet.stat_type and bet.stat_type.lower() == 'total')
            if is_totals and game and game.home_score is not None and game.away_score is not None:
                value = game.home_score + game.away_score
                bet.result_value = value
                line = 0.0
                if bet.selection:
                    import re
                    numbers = re.findall(r'[-+]?\d*\.?\d+', bet.selection)
                    if numbers:
                        line = float(numbers[-1])
                if "over" in sel:
                    bet.status = "won" if value > line else "lost"
                else:
                    bet.status = "won" if value < line else "lost"
                bet.graded_at = datetime.utcnow()
                bet.profit = self._calc_profit(bet)
                return {"bet_id": bet.id, "status": bet.status, "profit": bet.profit, "result_value": value}

            # Fallback: original player stat grading
            stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
            if not stat:
                logger.info(f"[Grader] Bet {bet.id}: Stats not found in DB for player {bet.player_id} game {bet.game_id}, fetching from ESPN...")
                stat = await self._fetch_player_stat_from_espn(bet.player_id, bet.game_id, game)
            if not stat:
                logger.warning(f"[Grader] Bet {bet.id}: Player stats not available (player_id={bet.player_id}, game_id={bet.game_id})")
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void", "reason": "Player stats not available"}
            stat_field = bet.stat_type or bet.market
            value = getattr(stat, stat_field, None)
            stats_json = getattr(stat, "stats_json", None)
            if value is None and stats_json and isinstance(stats_json, dict):
                value = stats_json.get(stat_field)
            # Enforce: cannot mark as won/lost unless stat value is present
            if value is None:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                bet.result_value = None
                return {"bet_id": bet.id, "status": "void", "reason": f"Stat '{stat_field}' not found"}
            try:
                value = float(value)
            except (TypeError, ValueError):
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                bet.result_value = None
                return {"bet_id": bet.id, "status": "void", "reason": "Invalid stat value"}
            bet.result_value = value
            line = 0.0
            if bet.selection:
                import re
                numbers = re.findall(r'[-+]?\d*\.?\d+', bet.selection)
                if numbers:
                    line = float(numbers[-1])
            # Only mark as won/lost if result_value is present
            if bet.result_value is None:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void", "reason": "No stat value for grading"}
            if "over" in sel:
                bet.status = "won" if value > line else "lost"
            else:
                bet.status = "won" if value < line else "lost"
            bet.graded_at = datetime.utcnow()
            bet.profit = self._calc_profit(bet)
            return {"bet_id": bet.id, "status": bet.status, "profit": bet.profit, "result_value": value}
        
        except Exception as e:
            logger.error("[Grader] Error grading prop bet %s: %s", bet.id, e, exc_info=True)
            bet.status = "void"
            bet.graded_at = datetime.utcnow()
            return {"bet_id": bet.id, "status": "void", "reason": f"Grading error: {str(e)}"}

    async def _grade_game(self, bet) -> Optional[Dict[str, Any]]:
        """Grade moneyline and spread bets based on game results"""
        if not bet.game_id:
            logger.warning(f"[Grader] Skipping bet {bet.id}: missing game_id")
            return None
        
        try:
            game = await self.games.get(bet.game_id)
            game_result = None
            if not game or not self._is_final_status(game.status):
                #logger.info(f"[Grader] Bet {bet.id}: game not final or not found (game_id={bet.game_id}, status={getattr(game, 'status', None)})")
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    #logger.info(f"[Grader] Bet {bet.id}: game_result not final or not found (game_id={bet.game_id}, status={getattr(game_result, 'status', None)})")
                    return None
                
                if game and game_result:
                    game.home_score = game_result.home_score
                    game.away_score = game_result.away_score
                    game.status = game_result.status
                    await self.session.flush()

            team_name = bet.selection.split()[0] if bet.selection else None
            if not team_name:
                logger.warning(f"[Grader] Bet {bet.id}: could not extract team name from selection '{bet.selection}'")
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            team_name_lower = team_name.lower()
            if game and game.home_team_name and game.away_team_name and game.home_score is not None:
                home_team_lower = (game.home_team_name or "").lower()
                away_team_lower = (game.away_team_name or "").lower()
                home_score = game.home_score or 0
                away_score = game.away_score or 0
            elif game_result:
                home_team_lower = (game_result.home_team_name or "").lower()
                away_team_lower = (game_result.away_team_name or "").lower()
                home_score = game_result.home_score or 0
                away_score = game_result.away_score or 0
            else:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            bet_on_home = team_name_lower in home_team_lower or home_team_lower in team_name_lower
            bet_on_away = team_name_lower in away_team_lower or away_team_lower in team_name_lower

            if not (bet_on_home or bet_on_away):
                logger.warning(f"[Grader] Bet {bet.id}: team name '{team_name_lower}' did not match home '{home_team_lower}' or away '{away_team_lower}'")
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            home_won = home_score > away_score

            if bet_on_home:
                bet.status = "won" if home_won else "lost"
            else:
                bet.status = "won" if not home_won else "lost"

            bet.graded_at = datetime.utcnow()
            bet.profit = self._calc_profit(bet)

            return {"bet_id": bet.id, "status": bet.status, "profit": bet.profit}
        
        except Exception as e:
            logger.error("[Grader] Error grading game bet %s: %s", bet.id, e, exc_info=True)
            bet.status = "void"
            bet.graded_at = datetime.utcnow()
            return {"bet_id": bet.id, "status": "void", "reason": f"Grading error: {str(e)}"}

    async def _get_game_result(self, game_id: str) -> Optional[GameResult]:
        stmt = select(GameResult).where(GameResult.game_id == game_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_player_stat_from_espn(self, player_id: str, game_id: str, game) -> Optional[Any]:
        """Fetch player stats from ESPN API if not in database"""
        try:
            sport = game.sport if hasattr(game, 'sport') else 'basketball'

            sport_map = {
                'basketball': ('basketball', 'nba'),
                'football': ('football', 'nfl'),
                'hockey': ('hockey', 'nhl'),
                'baseball': ('baseball', 'mlb'),
            }

            sport_type, league = sport_map.get(sport.lower(), ('basketball', 'nba'))

            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
            data = await self.espn_client.get_json(url)

            if not data or "boxscore" not in data:
                logger.debug("[Grader] No boxscore found for game %s at ESPN API", game_id)
                return None

            boxscore = data["boxscore"]
            players_by_team = boxscore.get("players", [])

            for team_players in players_by_team:
                statistics_groups = team_players.get("statistics", [])

                for stat_group in statistics_groups:
                    stat_labels = stat_group.get("labels", [])
                    athletes = stat_group.get("athletes", [])

                    for athlete_data in athletes:
                        athlete = athlete_data.get("athlete", {})
                        if str(athlete.get("id")) == str(player_id):
                            stats = athlete_data.get("stats", [])

                            from ...models.player_stats import PlayerStat

                            stat_obj = PlayerStat(
                                player_id=player_id,
                                game_id=game_id,
                                sport=sport,
                                stats_json={}
                            )

                            # Defensive: ensure stats_json is a dict
                            if stat_obj.stats_json is None:
                                stat_obj.stats_json = {}

                            for i, label in enumerate(stat_labels):
                                if i < len(stats):
                                    stat_obj.stats_json[label.lower()] = stats[i]

                            # Defensive: only assign int if possible
                            def safe_int(val):
                                try:
                                    return int(float(val))
                                except Exception:
                                    return None

                            if stat_obj.stats_json:
                                if 'pts' in stat_obj.stats_json or 'points' in stat_obj.stats_json:
                                    stat_obj.points = safe_int(stat_obj.stats_json.get('pts', stat_obj.stats_json.get('points', 0)))
                                if 'reb' in stat_obj.stats_json or 'rebounds' in stat_obj.stats_json:
                                    stat_obj.rebounds = safe_int(stat_obj.stats_json.get('reb', stat_obj.stats_json.get('rebounds', 0)))
                                if 'ast' in stat_obj.stats_json or 'assists' in stat_obj.stats_json:
                                    stat_obj.assists = safe_int(stat_obj.stats_json.get('ast', stat_obj.stats_json.get('assists', 0)))

                            self.session.add(stat_obj)
                            await self.session.flush()

                            return stat_obj

            logger.debug("[Grader] Player %s not found in boxscore for game %s", player_id, game_id)
            return None

        except Exception as e:
            logger.error("[Grader] Error fetching player stat from ESPN for player %s game %s: %s", 
                        player_id, game_id, e, exc_info=True)
            return None

    def _is_final_status(self, status: Optional[str]) -> bool:
        if not status:
            return False
        status_lower = status.lower()
        return (
            status_lower == "final"
            or "final" in status_lower
            or status_lower == "ft"
            or "ft" in status_lower
            or "full time" in status_lower
            or "full_time" in status_lower
            or status in ("STATUS_FINAL", "STATUS_FULL_TIME", "FT", "ft")
        )

    def _calc_profit(self, bet) -> float:
        if bet.status != "won":
            return -bet.stake

        if bet.odds > 0:
            return bet.stake * (bet.odds / 100)
        else:
            return bet.stake / (abs(bet.odds) / 100)