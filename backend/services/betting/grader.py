import logging
import re
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
        if (
            self._espn_client
            and hasattr(self._espn_client, "_session")
            and self._espn_client._session
        ):
            if not self._espn_client._session.closed:
                await self._espn_client.close()

    async def grade(self, bet) -> Optional[Dict[str, Any]]:
        if bet.bet_type in ("prop", "total"):
            result = await self._grade_prop(bet)
            if not result:
                logger.debug(
                    "[Grader] Bet %s not graded: _grade_prop returned None", bet.id
                )
            else:
                logger.debug("[Grader] Bet %s graded: %s", bet.id, result)
            return result

        if bet.bet_type in ("moneyline", "spread"):
            return await self._grade_game(bet)

        return None

    async def _grade_prop(self, bet) -> Optional[Dict[str, Any]]:
        if not bet.game_id:
            logger.warning(
                f"[Grader] Skipping bet {bet.id}: missing game_id (game_id={bet.game_id})"
            )
            return None

        try:
            game = await self.games.get(bet.game_id)
            if not game or not self._is_final_status(game.status):
                # logger.info(f"[Grader] Bet {bet.id}: game not final or not found (game_id={bet.game_id}, status={getattr(game, 'status', None)})")
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    # logger.info(f"[Grader] Bet {bet.id}: game_result not final or not found (game_id={bet.game_id}, status={getattr(game_result, 'status', None)})")
                    return None
                if game and game_result:
                    game.home_score = game_result.home_score
                    game.away_score = game_result.away_score
                    game.status = game_result.status
                    await self.session.flush()

            # Totals bet logic: only treat as game total if there's NO player attached
            sel = (bet.selection or "").strip().lower()
            is_totals = (not bet.player_id) and (
                "over" in sel
                or "under" in sel
                or (bet.stat_type and bet.stat_type.lower() == "total")
            )
            value: Optional[float] = None
            if (
                is_totals
                and game
                and game.home_score is not None
                and game.away_score is not None
            ):
                score: float = float(game.home_score + game.away_score)
                value = score
                bet.result_value = value
                line = 0.0
                if bet.selection:
                    numbers = re.findall(r"[-+]?\d*\.?\d+", bet.selection)
                    if numbers:
                        line = float(numbers[-1])
                if "over" in sel:
                    bet.status = "won" if score > line else "lost"
                else:
                    bet.status = "won" if score < line else "lost"
                bet.graded_at = datetime.utcnow()
                bet.profit = self._calc_profit(bet)
                return {
                    "bet_id": bet.id,
                    "status": bet.status,
                    "profit": bet.profit,
                    "result_value": value,
                }

            # Fallback: original player stat grading
            stat = await self.stats.get_for_player_game(bet.player_id, bet.game_id)
            if not stat:
                logger.info(
                    f"[Grader] Bet {bet.id}: Stats not found in DB for player {bet.player_id} game {bet.game_id}, fetching from ESPN..."
                )
                stat = await self._fetch_player_stat_from_espn(
                    bet.player_id, bet.game_id, game
                )
            if not stat:
                logger.warning(
                    f"[Grader] Bet {bet.id}: Player stats not available (player_id={bet.player_id}, game_id={bet.game_id})"
                )
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {
                    "bet_id": bet.id,
                    "status": "void",
                    "reason": "Player stats not available",
                }

            # Auto-void if player did not play (DNP / injured)
            minutes = getattr(stat, "minutes", None)
            try:
                if minutes is None:
                    min_val = None
                elif ":" in str(minutes):
                    # ESPN returns minutes as "MM:SS" — extract whole minutes
                    min_val = float(str(minutes).split(":")[0])
                else:
                    min_val = float(minutes)
            except (TypeError, ValueError):
                min_val = None
            if min_val is None or min_val == 0:
                logger.info(
                    f"[Grader] Bet {bet.id}: Player DNP (minutes={minutes}), voiding"
                )
                bet.status = "void"
                bet.result_value = None
                bet.graded_at = datetime.utcnow()
                bet.profit = 0
                return {
                    "bet_id": bet.id,
                    "status": "void",
                    "reason": "Player did not play (DNP)",
                }

            stat_field = bet.stat_type or bet.market

            # Guard: if no stat field at all, void the bet
            if not stat_field:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {
                    "bet_id": bet.id,
                    "status": "void",
                    "reason": "No stat_type or market defined",
                }

            # Normalise common shorthand names → PlayerStats column names
            _FIELD_ALIASES: dict = {
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
                "tov": "turnovers",
                "to": "turnovers",
                "turnovers": "turnovers",
                "pra": None,  # points+rebounds+assists – handled below
                "passing_yards": "passing_yards",
                "pass_yds": "passing_yards",
                "rushing_yards": "rushing_yards",
                "rush_yds": "rushing_yards",
                "receiving_yards": "receiving_yards",
                "rec_yds": "receiving_yards",
                "passing_tds": "passing_tds",
                "rush_tds": "rushing_tds",
                "receiving_tds": "receiving_tds",
                "hits": "hits",
                "hr": "hr",
                "rbi": "rbi",
                "sb": "sb",
                "goals": "nhl_goals",
                "nhl_goals": "nhl_goals",
                "shots": "nhl_shots",
                "nhl_shots": "nhl_shots",
            }
            stat_field_norm = stat_field.lower().strip()
            mapped_field = _FIELD_ALIASES.get(stat_field_norm, stat_field_norm)

            # Special combo stat: PRA = points + rebounds + assists
            stats_json = getattr(stat, "stats_json", None)
            if stat_field_norm == "pra":
                p = getattr(stat, "points", None) or 0
                r = getattr(stat, "rebounds", None) or 0
                a = getattr(stat, "assists", None) or 0
                value = float(p + r + a) if any([p, r, a]) else None
            elif mapped_field:
                raw = getattr(stat, mapped_field, None)
                if raw is None and stats_json and isinstance(stats_json, dict):
                    raw = (
                        stats_json.get(mapped_field)
                        or stats_json.get(stat_field_norm)
                        or stats_json.get(stat_field)
                    )
                value = float(raw) if raw is not None else None
            else:
                if stats_json and isinstance(stats_json, dict):
                    raw = stats_json.get(stat_field_norm) or stats_json.get(stat_field)
                    value = float(raw) if raw is not None else None
            # Enforce: cannot mark as won/lost unless stat value is present
            if value is None:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                bet.result_value = None
                return {
                    "bet_id": bet.id,
                    "status": "void",
                    "reason": f"Stat '{stat_field}' not found",
                }
            bet.result_value = value
            line = 0.0
            if bet.selection:
                numbers = re.findall(r"[-+]?\d*\.?\d+", bet.selection)
                if numbers:
                    line = float(numbers[-1])
            # Only mark as won/lost if result_value is present
            if bet.result_value is None:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {
                    "bet_id": bet.id,
                    "status": "void",
                    "reason": "No stat value for grading",
                }
            if "over" in sel:
                bet.status = "won" if value > line else "lost"
            else:
                bet.status = "won" if value < line else "lost"
            bet.graded_at = datetime.utcnow()
            bet.profit = self._calc_profit(bet)
            return {
                "bet_id": bet.id,
                "status": bet.status,
                "profit": bet.profit,
                "result_value": value,
            }

        except Exception as e:
            logger.error(
                "[Grader] Error grading prop bet %s: %s", bet.id, e, exc_info=True
            )
            bet.status = "void"
            bet.graded_at = datetime.utcnow()
            return {
                "bet_id": bet.id,
                "status": "void",
                "reason": f"Grading error: {str(e)}",
            }

    async def _grade_game(self, bet) -> Optional[Dict[str, Any]]:
        """Grade moneyline and spread bets based on game results"""
        if not bet.game_id:
            logger.warning(f"[Grader] Skipping bet {bet.id}: missing game_id")
            return None

        try:
            game = await self.games.get(bet.game_id)
            game_result = None
            if not game or not self._is_final_status(game.status):
                game_result = await self._get_game_result(bet.game_id)
                if not game_result or not self._is_final_status(game_result.status):
                    return None

                if game and game_result:
                    game.home_score = game_result.home_score
                    game.away_score = game_result.away_score
                    game.status = game_result.status
                    await self.session.flush()

            # ── Extract team name (everything before the bet-type keyword) ─────
            team_name = self._extract_team_name(bet.selection)
            if not team_name:
                logger.warning(
                    f"[Grader] Bet {bet.id}: could not extract team name from selection '{bet.selection}'"
                )
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            team_name_lower = team_name.lower()

            # ── ESPN is the authoritative final score; DB is fallback ──────────
            sport = (game.sport if game else None) or "basketball"
            espn_score = await self._fetch_espn_game_score(bet.game_id, sport)

            if espn_score:
                home_team_lower = espn_score[0].lower()
                away_team_lower = espn_score[1].lower()
                home_score: int = espn_score[2]
                away_score: int = espn_score[3]
                logger.debug(
                    "[Grader] Bet %s: ESPN final score %s %d – %d %s",
                    bet.id,
                    espn_score[0],
                    home_score,
                    away_score,
                    espn_score[1],
                )
            elif (
                game
                and game.home_team_name
                and game.away_team_name
                and game.home_score is not None
            ):
                home_team_lower = (game.home_team_name or "").lower()
                away_team_lower = (game.away_team_name or "").lower()
                home_score = game.home_score or 0
                away_score = game.away_score or 0
                logger.debug(
                    "[Grader] Bet %s: ESPN unavailable, using games table", bet.id
                )
            elif game_result:
                home_team_lower = (game_result.home_team_name or "").lower()
                away_team_lower = (game_result.away_team_name or "").lower()
                home_score = game_result.home_score or 0
                away_score = game_result.away_score or 0
                logger.debug(
                    "[Grader] Bet %s: ESPN unavailable, using games_results table",
                    bet.id,
                )
            else:
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            bet_on_home = (
                team_name_lower in home_team_lower or home_team_lower in team_name_lower
            )
            bet_on_away = (
                team_name_lower in away_team_lower or away_team_lower in team_name_lower
            )

            if not (bet_on_home or bet_on_away):
                logger.warning(
                    "[Grader] Bet %s: team '%s' matched neither home '%s' nor away '%s'",
                    bet.id,
                    team_name_lower,
                    home_team_lower,
                    away_team_lower,
                )
                bet.status = "void"
                bet.graded_at = datetime.utcnow()
                return {"bet_id": bet.id, "status": "void"}

            if bet.bet_type == "spread":
                # Extract the spread line from the selection (e.g. "Knicks -6.5" → -6.5)
                spread_line = 0.0
                if bet.selection:
                    # Last numeric token (with optional sign) is the spread value
                    raw_spread = None
                    sel_parts = bet.selection.split()
                    for part in reversed(sel_parts):
                        m = re.match(r"^([+\-]?\d+\.?\d*)$", part)
                        if m:
                            raw_spread = m.group(1)
                            break
                    if raw_spread is not None:
                        spread_line = float(raw_spread)

                logger.info(
                    "[Grader] Spread bet %s: selection='%s', team='%s', spread_line=%s, home=%s %d, away=%s %d, bet_on_home=%s, bet_on_away=%s",
                    bet.id,
                    bet.selection,
                    team_name_lower,
                    spread_line,
                    home_team_lower,
                    home_score,
                    away_team_lower,
                    away_score,
                    bet_on_home,
                    bet_on_away,
                )

                # Apply spread from the perspective of the betted team.
                # If bet is on home team: home_score + spread vs away_score
                if bet_on_home:
                    adjusted = home_score + spread_line
                    if adjusted > away_score:
                        bet.status = "won"
                    elif adjusted == away_score:
                        bet.status = "push"
                    else:
                        bet.status = "lost"
                else:
                    adjusted = away_score + spread_line
                    if adjusted > home_score:
                        bet.status = "won"
                    elif adjusted == home_score:
                        bet.status = "push"
                    else:
                        bet.status = "lost"

                logger.info(
                    "[Grader] Spread result: bet_id=%s, selection='%s', spread_line=%s, home=%d, away=%d, bet_on_home=%s, bet_on_away=%s, adjusted=%s -> %s",
                    bet.id,
                    bet.selection,
                    spread_line,
                    home_score,
                    away_score,
                    bet_on_home,
                    bet_on_away,
                    adjusted,
                    bet.status,
                )

                logger.debug(
                    "[Grader] Bet %s spread: team=%s line=%s home=%d away=%d adjusted=%s → %s",
                    bet.id,
                    team_name_lower,
                    spread_line,
                    home_score,
                    away_score,
                    adjusted,
                    bet.status,
                )
            else:
                # Moneyline: straight win/loss
                home_won = home_score > away_score
                if bet_on_home:
                    bet.status = "won" if home_won else "lost"
                else:
                    bet.status = "won" if not home_won else "lost"

            bet.graded_at = datetime.utcnow()
            bet.profit = self._calc_profit(bet)

            logger.info(
                "[Grader] Bet %s (%s) graded as %s: home=%s %d, away=%s %d",
                bet.id,
                bet.selection,
                bet.status,
                home_team_lower,
                home_score,
                away_team_lower,
                away_score,
            )

            return {"bet_id": bet.id, "status": bet.status, "profit": bet.profit}

        except Exception as e:
            logger.error(
                "[Grader] Error grading game bet %s: %s", bet.id, e, exc_info=True
            )
            bet.status = "void"
            bet.graded_at = datetime.utcnow()
            return {
                "bet_id": bet.id,
                "status": "void",
                "reason": f"Grading error: {str(e)}",
            }

    async def _get_game_result(self, game_id: str) -> Optional[GameResult]:
        stmt = select(GameResult).where(GameResult.game_id == game_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _extract_team_name(self, selection: Optional[str]) -> Optional[str]:
        """
        Extract the team name from a selection string.

        Examples:
          'Warriors ML'                 → 'Warriors'
          'Golden State Warriors ML'    → 'Golden State Warriors'
          'Celtics -3.5'                → 'Celtics'
          'Over 215.5'                  → None  (totals handled elsewhere)
        """
        if not selection:
            return None
        _STOP_WORDS = {"ml", "moneyline", "spread", "total", "over", "under", "pk"}
        parts = selection.split()
        team_words = []
        for part in parts:
            if part.lower() in _STOP_WORDS:
                break
            # Stop at numeric spread/total values like +3.5, -7, O45.5, U220
            if re.match(r"^[+\-ouOU]?\d", part):
                break
            team_words.append(part)
        if team_words:
            return " ".join(team_words)
        # Last resort: use the raw first word
        return parts[0] if parts else None

    async def _fetch_espn_game_score(
        self,
        game_id: str,
        sport: str = "basketball",
    ) -> Optional[tuple]:
        """
        Fetch the definitive final score from the ESPN summary API.

        Returns (home_team_name, away_team_name, home_score, away_score) or None
        if the game is not yet complete or the API is unavailable.
        """
        sport_map = {
            "basketball": ("basketball", "nba"),
            "football": ("football", "nfl"),
            "hockey": ("hockey", "nhl"),
            "baseball": ("baseball", "mlb"),
        }
        sport_type, league = sport_map.get((sport or "").lower(), ("basketball", "nba"))
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports"
            f"/{sport_type}/{league}/summary?event={game_id}"
        )
        data = await self.espn_client.get_json(url)
        if not data:
            return None
        try:
            competitions = data.get("header", {}).get("competitions", [])
            if not competitions:
                return None
            comp = competitions[0]
            # Only grade when ESPN also says the game is complete
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                return None
            home_team: Optional[str] = None
            away_team: Optional[str] = None
            home_score: Optional[int] = None
            away_score: Optional[int] = None
            for competitor in comp.get("competitors", []):
                ha = competitor.get("homeAway", "")
                team_name = competitor.get("team", {}).get(
                    "displayName"
                ) or competitor.get("team", {}).get("name", "")
                try:
                    score = int(competitor.get("score", ""))
                except (ValueError, TypeError):
                    score = None
                if ha == "home":
                    home_team, home_score = team_name, score
                elif ha == "away":
                    away_team, away_score = team_name, score
            if (
                home_team
                and away_team
                and home_score is not None
                and away_score is not None
            ):
                return (home_team, away_team, home_score, away_score)
            return None
        except Exception as exc:
            logger.debug("[Grader] ESPN score parse error for %s: %s", game_id, exc)
            return None

    async def _fetch_player_stat_from_espn(
        self, player_id: str, game_id: str, game
    ) -> Optional[Any]:
        """Fetch player stats from ESPN API if not in database"""
        try:
            sport = game.sport if hasattr(game, "sport") else "basketball"

            sport_map = {
                "basketball": ("basketball", "nba"),
                "football": ("football", "nfl"),
                "hockey": ("hockey", "nhl"),
                "baseball": ("baseball", "mlb"),
            }

            sport_type, league = sport_map.get(sport.lower(), ("basketball", "nba"))

            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/summary?event={game_id}"
            data = await self.espn_client.get_json(url)

            if not data or "boxscore" not in data:
                logger.debug(
                    "[Grader] No boxscore found for game %s at ESPN API", game_id
                )
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
                                stats_json={},
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
                                if "min" in stat_obj.stats_json:
                                    stat_obj.minutes = str(stat_obj.stats_json["min"])
                                if (
                                    "pts" in stat_obj.stats_json
                                    or "points" in stat_obj.stats_json
                                ):
                                    stat_obj.points = safe_int(
                                        stat_obj.stats_json.get(
                                            "pts", stat_obj.stats_json.get("points", 0)
                                        )
                                    )
                                if (
                                    "reb" in stat_obj.stats_json
                                    or "rebounds" in stat_obj.stats_json
                                ):
                                    stat_obj.rebounds = safe_int(
                                        stat_obj.stats_json.get(
                                            "reb",
                                            stat_obj.stats_json.get("rebounds", 0),
                                        )
                                    )
                                if (
                                    "ast" in stat_obj.stats_json
                                    or "assists" in stat_obj.stats_json
                                ):
                                    stat_obj.assists = safe_int(
                                        stat_obj.stats_json.get(
                                            "ast", stat_obj.stats_json.get("assists", 0)
                                        )
                                    )

                            self.session.add(stat_obj)
                            await self.session.flush()

                            return stat_obj

            logger.debug(
                "[Grader] Player %s not found in boxscore for game %s",
                player_id,
                game_id,
            )
            return None

        except Exception as e:
            logger.error(
                "[Grader] Error fetching player stat from ESPN for player %s game %s: %s",
                player_id,
                game_id,
                e,
                exc_info=True,
            )
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
        """Calculate profit using American odds (e.g. -182, +150)."""
        if bet.status != "won":
            return -bet.stake
        odds = bet.odds
        stake = bet.stake
        # Decimal odds (1.01–99 range) stored from older bets — handle gracefully
        if 1.01 <= odds < 100:
            return round(stake * (odds - 1), 2)
        # American odds
        if odds > 0:
            return round(stake * (odds / 100), 2)
        else:
            return round(stake * (100 / abs(odds)), 2)
