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
        self.espn_client = ESPNClient()

    async def close(self):
        """Clean up resources"""
        await self.espn_client.close()

    async def grade(self, bet) -> Optional[Dict[str, Any]]:
        if bet.bet_type == "prop":
            return await self._grade_prop(bet)

        if bet.bet_type in ("moneyline", "spread"):
            return await self._grade_game(bet)

        return None

    async def _grade_prop(self, bet) -> Optional[Dict[str, Any]]:
        if not bet.player_id or not bet.game_id:
            logger.debug("[Grader] Skipping bet %s: missing player_id or game_id", bet.id)
            return None

        try:
            game = await self.games.get(bet.game_id)
            if not game or not self._is_final_status(game.status):
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    logger.debug(
                        "[Grader] Skipping bet %s: game not final. Game status=%s, GameResult status=%s",
                        bet.id,
                        game.status if game else "none",
                        game_result.status if game_result else "none",
                    )
                    return None

            stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
            
            # If stat not found in DB, try fetching from ESPN API
            if not stat:
                logger.debug(
                    "Stats not found in DB for player %s game %s, fetching from ESPN...",
                    bet.player_id,
                    bet.game_id,
                )
                stat = await self._fetch_player_stat_from_espn(bet.player_id, bet.game_id, game)
                
            if not stat:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void", "reason": "Player stats not available"}

            # Use stat_type (e.g., "points", "rebounds") instead of market (e.g., "over", "under")
            stat_field = bet.stat_type or bet.market
            value = getattr(stat, stat_field, None)
            if value is None and getattr(stat, "stats_json", None):
                value = stat.stats_json.get(stat_field)
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

            # Extract the line value from selection (e.g., "Jalen Brunson over 27.5 pts" -> 27.5)
            line = 0.0
            if bet.selection:
                import re
                # Look for a number in the selection string
                numbers = re.findall(r'[-+]?\d*\.?\d+', bet.selection)
                if numbers:
                    line = float(numbers[-1])  # Use the last number found
            
            sel = (bet.selection or "").strip().lower()

            # Check if "over" appears anywhere in the selection
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
            logger.debug("[Grader] Skipping bet %s: missing game_id", bet.id)
            return None
        
        try:
            game = await self.games.get(bet.game_id)
            game_result = None
            if not game or not self._is_final_status(game.status):
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    logger.debug(
                        "[Grader] Skipping bet %s: game not final. Game status=%s, GameResult status=%s",
                        bet.id,
                        game.status if game else "none",
                        game_result.status if game_result else "none",
                    )
                    return None
                
                # If using game_result, update the game object with final scores
                if game and game_result:
                    game.home_score = game_result.home_score
                    game.away_score = game_result.away_score
                    game.status = game_result.status
                    await self.session.flush()

            # Extract team name from selection (e.g., "Celtics ML" -> "Celtics")
            team_name = bet.selection.split()[0] if bet.selection else None
            if not team_name:
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

            # Determine which team the bet was on
            bet_on_home = team_name_lower in home_team_lower or home_team_lower in team_name_lower
            bet_on_away = team_name_lower in away_team_lower or away_team_lower in team_name_lower

            if not (bet_on_home or bet_on_away):
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            # Check if the team won
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
            # Determine sport type and league from game
            sport = game.sport if hasattr(game, 'sport') else 'basketball'
            
            # Map sport names to ESPN API paths
            sport_map = {
                'basketball': ('basketball', 'nba'),
                'football': ('football', 'nfl'),
                'hockey': ('hockey', 'nhl'),
                'baseball': ('baseball', 'mlb'),
            }
            
            sport_type, league = sport_map.get(sport.lower(), ('basketball', 'nba'))
            
            # Fetch game summary from ESPN
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
            data = await self.espn_client.get_json(url)
            
            if not data or "boxscore" not in data:
                logger.debug("[Grader] No boxscore found for game %s at ESPN API", game_id)
                return None
            
            boxscore = data["boxscore"]
            players_by_team = boxscore.get("players", [])
            
            # Search for the player in the boxscore
            for team_players in players_by_team:
                statistics_groups = team_players.get("statistics", [])
                
                for stat_group in statistics_groups:
                    stat_labels = stat_group.get("labels", [])
                    athletes = stat_group.get("athletes", [])
                    
                    for athlete_data in athletes:
                        athlete = athlete_data.get("athlete", {})
                        if str(athlete.get("id")) == str(player_id):
                            stats = athlete_data.get("stats", [])
                            
                            # Create a temporary stats object with the data
                            from ...models.player_stats import PlayerStat
                            
                            stat_obj = PlayerStat(
                                player_id=player_id,
                                game_id=game_id,
                                sport=sport,
                                stats_json={}
                            )
                            
                            # Map stat labels to values
                            for i, label in enumerate(stat_labels):
                                if i < len(stats):
                                    stat_obj.stats_json[label.lower()] = stats[i]
                            
                            # Also set common attributes if they exist
                            if 'pts' in stat_obj.stats_json or 'points' in stat_obj.stats_json:
                                stat_obj.points = float(stat_obj.stats_json.get('pts', stat_obj.stats_json.get('points', 0)))
                            if 'reb' in stat_obj.stats_json or 'rebounds' in stat_obj.stats_json:
                                stat_obj.rebounds = float(stat_obj.stats_json.get('reb', stat_obj.stats_json.get('rebounds', 0)))
                            if 'ast' in stat_obj.stats_json or 'assists' in stat_obj.stats_json:
                                stat_obj.assists = float(stat_obj.stats_json.get('ast', stat_obj.stats_json.get('assists', 0)))
                            
                            # Save to database for future use
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
        # Recognize various final status indicators
        return (
            status_lower == "final" 
            or "final" in status_lower 
            or "full time" in status_lower
            or "full_time" in status_lower
            or status in ("STATUS_FINAL", "STATUS_FULL_TIME")
        )

    def _calc_profit(self, bet) -> float:
        if bet.status != "won":
            return -bet.stake

        if bet.odds > 0:
            return bet.stake * (bet.odds / 100)
        else:
            return bet.stake / (abs(bet.odds) / 100)