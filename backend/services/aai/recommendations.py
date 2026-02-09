from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import combinations
import math
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.game import Game
from ...models.games_results import GameResult
from ...models.games_upcoming import GameUpcoming
from ...models.games_live import GameLive
from ...models.injury import Injury
from ..weather import WeatherService


class ExternalOddsAggregator:
    """Aggregates probabilities from multiple external model sources."""

    DEFAULT_MODELS = {"all"}
    SUPPORTED_MODELS = {"all", "vegas", "elo", "ml", "kelly", "home_advantage"}

    @staticmethod
    def implied_probability_from_moneyline(moneyline: int) -> float:
        """Convert American moneyline odds to implied probability."""
        if moneyline == 0:
            return 0.5
        if moneyline > 0:
            return 100 / (moneyline + 100)
        else:
            return abs(moneyline) / (abs(moneyline) + 100)

    @staticmethod
    def moneyline_from_probability(probability: float) -> int:
        """Convert probability to American moneyline odds."""
        if probability <= 0 or probability >= 1:
            return 0
        if probability > 0.5:
            return int(-100 * probability / (1 - probability))
        else:
            return int(100 * (1 - probability) / probability)

    async def fetch_external_odds(
        self,
        game: Optional[Game],
        team_name: str,
        is_home: bool,
        models: Optional[set[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Fetch and aggregate external probability models for a given team/game.
        
        Returns:
            Dict with keys for each model and 'mean' for the aggregated probability.
        """
        probabilities: Dict[str, float] = {}
        context = context or {}
        enabled_models = self._normalize_models(models)
        use_all = "all" in enabled_models

        # Home field advantage
        # Empirical: home teams win ~53-55% across sports
        if use_all or "home_advantage" in enabled_models:
            home_advantage_prob = 0.54 if is_home else 0.46
            probabilities["home_advantage"] = home_advantage_prob

        # Elo model
        if use_all or "elo" in enabled_models:
            elo_prob = await self._get_elo_probability(game, team_name, is_home, context)
            if elo_prob is not None:
                probabilities["elo"] = elo_prob

        # Vegas implied probability
        if use_all or "vegas" in enabled_models:
            vegas_prob = await self._get_vegas_implied_probability(game, team_name, is_home, context)
            if vegas_prob is not None:
                probabilities["vegas"] = vegas_prob

        # Predictive ML model
        if use_all or "ml" in enabled_models:
            predictive_prob = await self._get_predictive_model_probability(game, team_name, is_home, context)
            if predictive_prob is not None:
                probabilities["ml"] = predictive_prob

        # Kelly-based adjustment model
        if use_all or "kelly" in enabled_models:
            kelly_prob = await self._get_kelly_probability(game, team_name, is_home, context)
            if kelly_prob is not None:
                probabilities["kelly"] = kelly_prob

        # Calculate mean of all available models
        if probabilities:
            mean_prob = sum(probabilities.values()) / len(probabilities)
            probabilities["mean"] = mean_prob
        else:
            probabilities["mean"] = 0.5

        return probabilities

    def get_consensus_strength(self, probabilities: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze consensus strength across models.
        
        Returns confidence score (0-100) indicating model agreement.
        High agreement = high confidence; disagreement = uncertainty signal.
        """
        # Extract only model probabilities (exclude 'mean')
        model_probs = [v for k, v in probabilities.items() if k != 'mean']
        
        if len(model_probs) < 2:
            return {
                "consensus_strength": 0,
                "consensus_probability": probabilities.get("mean", 0.5),
                "model_agreement": 0,
                "is_confident": False,
                "models_count": len(model_probs)
            }
        
        # Calculate standard deviation (lower = more agreement)
        mean_prob = sum(model_probs) / len(model_probs)
        variance = sum((p - mean_prob) ** 2 for p in model_probs) / len(model_probs)
        std_dev = math.sqrt(variance)
        
        # Convert std dev to confidence (0-100)
        # 0 std dev = 100% confidence, 0.5 std dev = 0% confidence
        confidence = max(0, 100 * (1 - (std_dev * 2)))
        
        # Model agreement: % of models predicting same winner
        consensus_pick = mean_prob > 0.5
        agreeing_models = sum(1 for p in model_probs if (p > 0.5) == consensus_pick)
        agreement_rate = (agreeing_models / len(model_probs)) * 100
        
        return {
            "consensus_strength": round(confidence, 1),
            "consensus_probability": round(mean_prob, 3),
            "model_agreement": round(agreement_rate, 1),
            "is_confident": confidence >= 60,
            "models_count": len(model_probs),
            "std_deviation": round(std_dev, 3),
            "consensus_pick": "home_favorite" if mean_prob > 0.5 else "away_favorite",
            "edge_magnitude": round(abs(mean_prob - 0.5), 3)
        }
    
    def detect_contrarian_value(self, 
                               consensus_prob: float,
                               market_prob: float,
                               confidence: float) -> Dict[str, Any]:
        """
        Detect when models differ from market consensus.
        
        Contrarian value exists when:
        - Models + confidence level indicate undervalued pick
        - Market odds suggest different probability
        """
        model_edge = abs(consensus_prob - 0.5)
        market_edge = abs(market_prob - 0.5)
        
        # Value when model has stronger edge than market
        value_amount = model_edge - market_edge
        
        # Confidence adjustment - only trust high-confidence picks
        adjusted_value = value_amount * (confidence / 100)
        
        return {
            "has_contrarian_value": abs(adjusted_value) > 0.02,  # Threshold: 2% edge
            "value_amount": round(adjusted_value, 3),
            "model_edge": round(model_edge, 3),
            "market_edge": round(market_edge, 3),
            "pick_type": "undervalued" if adjusted_value > 0 else "overvalued",
            "confidence_adjusted": confidence >= 60 and abs(adjusted_value) > 0.02
        }

    async def _get_elo_probability(
        self, game: Game, team_name: str, is_home: bool, context: Dict[str, Any]
    ) -> Optional[float]:
        """Estimate Elo-based probability from recent team form."""
        home_form = context.get("home_form")
        away_form = context.get("away_form")
        if not home_form or not away_form:
            return None

        home_rating = 1500 + (home_form.win_rate - 0.5) * 400
        away_rating = 1500 + (away_form.win_rate - 0.5) * 400
        home_rating += 30  # small home advantage

        if is_home:
            diff = home_rating - away_rating
        else:
            diff = away_rating - home_rating

        prob = 1 / (1 + 10 ** (-diff / 400))
        return max(0.01, min(prob, 0.99))

    async def _get_vegas_implied_probability(
        self, game: Optional[Game], team_name: str, is_home: bool, context: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """Fetch Vegas line implied probability from stored odds JSON."""
        context = context or {}
        context_moneyline = context.get("odds_home") if is_home else context.get("odds_away")
        if context_moneyline is not None:
            try:
                return self.implied_probability_from_moneyline(int(context_moneyline))
            except (TypeError, ValueError):
                pass
        moneyline = self._extract_moneyline(game, is_home)
        if moneyline is None:
            return None
        return self.implied_probability_from_moneyline(moneyline)

    async def _get_predictive_model_probability(
        self, game: Game, team_name: str, is_home: bool, context: Dict[str, Any]
    ) -> Optional[float]:
        """Lightweight ML-style probability from recent form and home edge."""
        diff = context.get("form_diff")
        if diff is None:
            return None
        x = (diff * 3.0) + (0.2 if is_home else -0.2)
        prob = 1 / (1 + math.exp(-x))
        return max(0.01, min(prob, 0.99))

    async def _get_kelly_probability(
        self, game: Game, team_name: str, is_home: bool, context: Dict[str, Any]
    ) -> Optional[float]:
        """Kelly-adjusted probability using form confidence and market odds."""
        moneyline = self._extract_moneyline(game, is_home)
        form_confidence = context.get("form_confidence")
        if moneyline is None or form_confidence is None:
            return None

        decimal_odds = self._decimal_odds_from_moneyline(moneyline)
        if decimal_odds is None:
            return None
        b = decimal_odds - 1
        p = form_confidence
        q = 1 - p
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        if kelly_fraction <= 0:
            return None

        # Adjust probability slightly toward the edge suggested by Kelly sizing
        adjusted = p + (kelly_fraction * 0.05)
        return max(0.01, min(adjusted, 0.99))

    def _normalize_models(self, models: Optional[set[str]]) -> set[str]:
        if not models:
            return set(self.DEFAULT_MODELS)
        normalized = {m.strip().lower() for m in models if m}
        if not normalized:
            return set(self.DEFAULT_MODELS)
        if "all" in normalized:
            return {"all"}
        return normalized

    def _extract_moneyline(self, game: Optional[Game], is_home: bool) -> Optional[int]:
        if not game:
            return None
        for data in (game.lines_json, game.odds_history_json):
            moneyline = self._find_moneyline_in_data(data, is_home)
            if moneyline is not None:
                return moneyline
        return None

    def _find_moneyline_in_data(self, data: Any, is_home: bool) -> Optional[int]:
        if not data:
            return None
        if isinstance(data, list) and data:
            # Try most recent snapshot
            for item in reversed(data):
                moneyline = self._find_moneyline_in_data(item, is_home)
                if moneyline is not None:
                    return moneyline
            return None
        if isinstance(data, dict):
            home_ml = None
            away_ml = None

            if "items" in data and isinstance(data.get("items"), list):
                for item in reversed(data["items"]):
                    moneyline = self._find_moneyline_in_data(item, is_home)
                    if moneyline is not None:
                        return moneyline

            if "homeTeamOdds" in data or "awayTeamOdds" in data:
                home_ml = (data.get("homeTeamOdds") or {}).get("moneyline")
                away_ml = (data.get("awayTeamOdds") or {}).get("moneyline")

            if home_ml is None and away_ml is None and "moneyline" in data:
                ml = data.get("moneyline")
                if isinstance(ml, dict):
                    home_ml = ml.get("home")
                    away_ml = ml.get("away")
                elif isinstance(ml, (int, float)):
                    home_ml = ml if is_home else None
                    away_ml = ml if not is_home else None

            if home_ml is None and away_ml is None:
                home_ml = data.get("home")
                away_ml = data.get("away")

            target = home_ml if is_home else away_ml
            if isinstance(target, str):
                try:
                    target = int(float(target))
                except ValueError:
                    return None
            if isinstance(target, (int, float)):
                return int(target)

        return None

    def _decimal_odds_from_moneyline(self, moneyline: int) -> Optional[float]:
        if moneyline == 0:
            return None
        if moneyline > 0:
            return 1 + (moneyline / 100)
        return 1 + (100 / abs(moneyline))


@dataclass
class TeamForm:
    team_name: str
    games: int
    wins: int

    @property
    def win_rate(self) -> float:
        if self.games == 0:
            return 0.0
        return self.wins / self.games


class AAIBetRecommender:
    """Data-driven betting suggestions based on recent team results and external model probabilities."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.odds_aggregator = ExternalOddsAggregator()
        self.weather_service = WeatherService()

    async def generate(
        self,
        days_ahead: int = 1,
        lookback_games: int = 5,
        lookback_days: int = 90,
        max_singles: int = 12,
        parlay_sizes: Tuple[int, ...] = (2, 3, 4, 5, 7, 12),
        include_external_odds: bool = True,
        external_models: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        pst = ZoneInfo("America/Los_Angeles")
        now_pst = now_utc.astimezone(pst)
        day_start_pst = datetime(
            year=now_pst.year,
            month=now_pst.month,
            day=now_pst.day,
            tzinfo=pst,
        )
        day_end_pst = day_start_pst + timedelta(days=days_ahead)

        candidates = await self._load_candidate_games(day_start_pst, day_end_pst)

        singles: List[Dict[str, Any]] = []

        for candidate in candidates:
            game = candidate["game"]
            if not candidate["home_team_name"] or not candidate["away_team_name"]:
                continue

            home_form = await self._team_form(
                team_id=candidate["home_team_id"],
                team_name=candidate["home_team_name"],
                lookback_games=lookback_games,
                lookback_days=lookback_days,
            )
            away_form = await self._team_form(
                team_id=candidate["away_team_id"],
                team_name=candidate["away_team_name"],
                lookback_games=lookback_games,
                lookback_days=lookback_days,
            )

            if not home_form or not away_form:
                continue

            diff = home_form.win_rate - away_form.win_rate
            if diff == 0:
                continue

            pick_home = diff > 0
            pick_team = candidate["home_team_name"] if pick_home else candidate["away_team_name"]
            pick_team_id = candidate["home_team_id"] if pick_home else candidate["away_team_id"]
            form_confidence = 0.5 + abs(diff) / 2
            form_confidence = max(0.51, min(form_confidence, 0.85))

            # ✅ NEW: Check for injuries affecting confidence
            injury_impact = await self._check_injury_impact(
                pick_team_id, 
                candidate["home_team_id"], 
                candidate["away_team_id"]
            )
            
            # ✅ NEW: Check weather impact on confidence
            weather_impact = await self._check_weather_impact(
                candidate,
                game
            )

            # Fetch and aggregate external odds if enabled
            external_odds = None
            combined_confidence = form_confidence
            if include_external_odds:
                context = {
                    "home_form": home_form,
                    "away_form": away_form,
                    "form_confidence": form_confidence,
                    "form_diff": diff,
                    "odds_home": candidate.get("odds_home"),
                    "odds_away": candidate.get("odds_away"),
                }
                external_odds = await self.odds_aggregator.fetch_external_odds(
                    game,
                    pick_team,
                    pick_home,
                    models=external_models,
                    context=context,
                )
                # Blend form-based confidence with external odds mean
                if external_odds and "mean" in external_odds:
                    external_prob = external_odds["mean"]
                    # Simple blend: 50/50 weight between form analysis and external models
                    combined_confidence = (form_confidence + external_prob) / 2
            
            # ✅ NEW: Apply injury and weather adjustments to confidence
            combined_confidence = combined_confidence * injury_impact["confidence_multiplier"]
            combined_confidence = combined_confidence * weather_impact["confidence_multiplier"]
            combined_confidence = max(0.01, min(combined_confidence, 0.99))

            reason = (
                f"Recent form: {home_form.team_name} {home_form.wins}/{home_form.games} "
                f"({home_form.win_rate:.0%}) vs {away_form.team_name} "
                f"{away_form.wins}/{away_form.games} ({away_form.win_rate:.0%})"
            )
            
            # ✅ NEW: Add injury/weather warnings to reason
            warnings = []
            if injury_impact["key_players_out"] > 0:
                warnings.append(f"⚠️ {injury_impact['key_players_out']} key injuries")
            if weather_impact["is_harsh"]:
                warnings.append(f"🌧️ Harsh weather: {weather_impact['description']}")
            
            if warnings:
                reason += " | " + ", ".join(warnings)

            single_data = {
                "game_id": candidate["game_id"],
                "start_time": candidate["start_time"].isoformat() if candidate["start_time"] else None,
                "home": candidate["home_team_name"],
                "away": candidate["away_team_name"],
                "pick": pick_team,
                "confidence": round(form_confidence * 100, 1),
                "combined_confidence": round(combined_confidence * 100, 1),
                "reason": reason,
                "data_points": {
                    "home_games": home_form.games,
                    "away_games": away_form.games,
                },
                # ✅ NEW: Include injury and weather data
                "injury_impact": injury_impact,
                "weather_impact": weather_impact
            }

            # Include external odds if available
            if external_odds:
                single_data["external_odds"] = {
                    k: round(v * 100, 1) if isinstance(v, float) else v
                    for k, v in external_odds.items()
                }

            singles.append(single_data)

        singles.sort(key=lambda s: s["combined_confidence"], reverse=True)
        singles = singles[:max_singles]

        parlays = self._build_parlays(singles, parlay_sizes)

        # Convert candidates to upcoming_games format for frontend
        upcoming_games = [
            {
                "game_id": c["game_id"],
                "sport": c["game"].sport if c["game"] else "unknown",
                "start_time": c["start_time"].isoformat() if c["start_time"] else None,
                "home": c["home_team_name"],
                "away": c["away_team_name"],
                "home_team_id": c.get("home_team_id"),
                "away_team_id": c.get("away_team_id"),
            }
            for c in candidates
        ]

        return {
            "generated_at": now_utc.isoformat(),
            "singles": singles,
            "parlays": parlays,
            "upcoming_games": upcoming_games,
            "external_models": sorted(external_models or self.odds_aggregator.DEFAULT_MODELS),
            "disclaimer": (
                "These recommendations blend recent team form with external probability models. "
                "They are not guarantees. Always bet responsibly."
            ),
        }

    async def _team_form(
        self,
        team_id: Optional[str],
        team_name: Optional[str],
        lookback_games: int,
        lookback_days: int,
    ) -> Optional[TeamForm]:
        if not team_id and not team_name:
            return None

        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        filters = [GameResult.start_time.is_not(None), GameResult.start_time >= cutoff]
        if team_id:
            filters.append(or_(GameResult.home_team_id == team_id, GameResult.away_team_id == team_id))
        else:
            filters.append(
                or_(
                    GameResult.home_team_name == team_name,
                    GameResult.away_team_name == team_name,
                )
            )

        stmt = (
            select(GameResult)
            .where(*filters)
            .order_by(GameResult.start_time.desc())
            .limit(lookback_games)
        )
        result = await self.session.execute(stmt)
        games = result.scalars().all()

        if not games:
            return None

        wins = 0
        team_display = team_name or "Unknown"
        for g in games:
            home_score = g.home_score or 0
            away_score = g.away_score or 0
            if team_id:
                if g.home_team_id == team_id:
                    team_display = g.home_team_name or team_display
                    if home_score > away_score:
                        wins += 1
                elif g.away_team_id == team_id:
                    team_display = g.away_team_name or team_display
                    if away_score > home_score:
                        wins += 1
            else:
                if g.home_team_name == team_name:
                    if home_score > away_score:
                        wins += 1
                elif g.away_team_name == team_name:
                    if away_score > home_score:
                        wins += 1

        return TeamForm(team_name=team_display, games=len(games), wins=wins)

    def _build_parlays(self, singles: List[Dict[str, Any]], sizes: Tuple[int, ...]) -> List[Dict[str, Any]]:
        parlays: List[Dict[str, Any]] = []
        if not singles:
            return parlays

        for size in sizes:
            if len(singles) < size:
                continue
            size_parlays: List[Dict[str, Any]] = []
            for combo in combinations(singles, size):
                confidence = 1.0
                combined_confidence = 1.0
                legs = []
                for leg in combo:
                    # Use combined confidence (blend of form + external) if available
                    leg_confidence = leg.get("combined_confidence", leg["confidence"]) / 100
                    confidence *= max(0.01, leg["confidence"] / 100)
                    combined_confidence *= max(0.01, leg_confidence)
                    legs.append({
                        "game_id": leg["game_id"],
                        "pick": leg["pick"],
                        "confidence": leg["confidence"],
                        "combined_confidence": leg.get("combined_confidence", leg["confidence"]),
                    })

                size_parlays.append(
                    {
                        "legs": legs,
                        "leg_count": size,
                        "confidence": round(confidence * 100, 1),
                        "combined_confidence": round(combined_confidence * 100, 1),
                    }
                )

            size_parlays.sort(key=lambda p: p["combined_confidence"], reverse=True)
            parlays.extend(size_parlays[:3])

        parlays.sort(key=lambda p: p["combined_confidence"], reverse=True)
        return parlays

    async def _load_candidate_games(self, day_start_pst: datetime, day_end_pst: datetime) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        upcoming_stmt = (
            select(GameUpcoming)
            .options(selectinload(GameUpcoming.game))
            .where(GameUpcoming.start_time.is_not(None))
            .order_by(GameUpcoming.start_time.asc())
        )
        upcoming_result = await self.session.execute(upcoming_stmt)
        upcoming_games = upcoming_result.scalars().all()

        for upcoming in upcoming_games:
            game = upcoming.game
            if not game:
                game = await self.session.get(Game, upcoming.game_id)
            start_time = upcoming.start_time or (game.start_time if game else None)
            if not start_time:
                continue
            start_time_pst = self._to_pst(start_time)
            if start_time_pst is None:
                continue
            if not (day_start_pst <= start_time_pst < day_end_pst):
                continue
            status = (upcoming.status or (game.status if game else None) or "").lower()
            if "final" in status:
                continue
            candidates.append(
                {
                    "game": game,
                    "game_id": upcoming.game_id,
                    "start_time": start_time,
                    "home_team_name": upcoming.home_team_name or (game.home_team_name if game else None),
                    "away_team_name": upcoming.away_team_name or (game.away_team_name if game else None),
                    "home_team_id": upcoming.home_team_id or (game.home_team_id if game else None),
                    "away_team_id": upcoming.away_team_id or (game.away_team_id if game else None),
                    "odds_home": upcoming.odds_home,
                    "odds_away": upcoming.odds_away,
                }
            )

        if candidates:
            return candidates

        live_stmt = (
            select(GameLive)
            .options(selectinload(GameLive.game))
            .order_by(GameLive.updated_at.desc())
            .limit(50)
        )
        live_result = await self.session.execute(live_stmt)
        live_games = live_result.scalars().all()
        for live in live_games:
            game = live.game
            if not game:
                game = await self.session.get(Game, live.game_id)
            if not game:
                continue
            start_time = game.start_time or live.updated_at
            if start_time:
                start_time_pst = self._to_pst(start_time)
                if start_time_pst and not (day_start_pst <= start_time_pst < day_end_pst):
                    continue
            status = (live.status or game.status or "").lower()
            if "final" in status:
                continue
            candidates.append(
                {
                    "game": game,
                    "game_id": live.game_id,
                    "start_time": start_time,
                    "home_team_name": live.home_team_name or game.home_team_name,
                    "away_team_name": live.away_team_name or game.away_team_name,
                    "home_team_id": game.home_team_id,
                    "away_team_id": game.away_team_id,
                    "odds_home": None,
                    "odds_away": None,
                }
            )

        if candidates:
            return candidates

        fallback_stmt = (
            select(Game)
            .where(or_(Game.status.is_(None), ~Game.status.ilike("%final%")))
            .where(Game.start_time.is_not(None))
            .order_by(Game.start_time.asc())
        )
        fallback_result = await self.session.execute(fallback_stmt)
        for game in fallback_result.scalars().all():
            start_time = game.start_time
            if not start_time:
                continue
            start_time_pst = self._to_pst(start_time)
            if start_time_pst is None:
                continue
            if not (day_start_pst <= start_time_pst < day_end_pst):
                continue
            candidates.append(
                {
                    "game": game,
                    "game_id": game.game_id,
                    "start_time": start_time,
                    "home_team_name": game.home_team_name,
                    "away_team_name": game.away_team_name,
                    "home_team_id": game.home_team_id,
                    "away_team_id": game.away_team_id,
                    "odds_home": None,
                    "odds_away": None,
                }
            )

        return candidates

    def _to_pst(self, value: Any) -> Optional[datetime]:
        pst = ZoneInfo("America/Los_Angeles")
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=pst)
            return value.astimezone(pst)
        return None    
    async def _check_injury_impact(self, pick_team_id: str, home_team_id: str, away_team_id: str) -> Dict[str, Any]:
        """
        Check injury impact on bet confidence.
        Returns impact assessment and confidence multiplier.
        """
        # Get injuries for both teams
        stmt = select(Injury).where(
            or_(
                Injury.team_id == home_team_id,
                Injury.team_id == away_team_id
            )
        )
        result = await self.session.execute(stmt)
        injuries = result.scalars().all()
        
        if not injuries:
            return {
                "key_players_out": 0,
                "total_injuries": 0,
                "confidence_multiplier": 1.0,
                "description": "No injuries reported"
            }
        
        # Count injuries by team
        pick_team_injuries = [inj for inj in injuries if inj.team_id == pick_team_id]
        opponent_team_id = away_team_id if pick_team_id == home_team_id else home_team_id
        opponent_injuries = [inj for inj in injuries if inj.team_id == opponent_team_id]
        
        # Simple heuristic: key injuries reduce confidence
        key_positions = {"QB", "RB", "WR", "TE", "PG", "SG", "SF", "PF", "C"}
        pick_team_key_injuries = len([
            inj for inj in pick_team_injuries 
            if inj.status in ("Out", "Doubtful")
        ])
        opponent_key_injuries = len([
            inj for inj in opponent_injuries 
            if inj.status in ("Out", "Doubtful")
        ])
        
        # Adjust confidence based on injuries
        # If our pick has more key injuries, reduce confidence
        # If opponent has more, slightly increase
        net_injury_impact = opponent_key_injuries - pick_team_key_injuries
        
        if net_injury_impact >= 2:
            multiplier = 1.05  # Opponent much more injured, slight boost
        elif net_injury_impact == 1:
            multiplier = 1.02
        elif net_injury_impact == 0:
            multiplier = 1.0
        elif net_injury_impact == -1:
            multiplier = 0.95  # Our pick more injured, reduce
        else:
            multiplier = 0.90  # Our pick significantly more injured
        
        return {
            "key_players_out": pick_team_key_injuries,
            "opponent_key_injuries": opponent_key_injuries,
            "total_injuries": len(injuries),
            "confidence_multiplier": multiplier,
            "description": f"{pick_team_key_injuries} key injuries (pick), {opponent_key_injuries} (opponent)"
        }
    
    async def _check_weather_impact(self, candidate: Dict[str, Any], game: Any) -> Dict[str, Any]:
        """
        Check weather impact on bet confidence.
        Returns impact assessment and confidence multiplier.
        """
        venue = candidate.get("venue") or (game.venue if hasattr(game, 'venue') else None)
        sport = game.sport if hasattr(game, 'sport') else None
        start_time = candidate.get("start_time")
        
        if not venue or not sport:
            return {
                "is_harsh": False,
                "confidence_multiplier": 1.0,
                "description": "Weather data unavailable"
            }
        
        # Indoor sports not affected
        if sport.upper() in ["NBA", "NCAAB", "NHL"]:
            return {
                "is_harsh": False,
                "confidence_multiplier": 1.0,
                "description": "Indoor sport - no weather impact"
            }
        
        # Get weather forecast
        weather_data = await self.weather_service.get_weather_impact_on_game(
            venue=venue,
            sport=sport,
            game_time=start_time
        )
        
        if not weather_data or not weather_data.get("weather"):
            return {
                "is_harsh": False,
                "confidence_multiplier": 1.0,
                "description": "Weather forecast unavailable"
            }
        
        weather = weather_data.get("weather", {})
        impact = weather_data.get("impact", {})
        
        is_harsh = weather.get("is_harsh", False)
        
        # Harsh weather reduces confidence slightly
        multiplier = 0.95 if is_harsh else 1.0
        
        # Also check overs adjustment (if game impacts scoring)
        overs_adj = impact.get("overs_adjustment", 1.0)
        if overs_adj < 0.95:
            # Significantly impacts scoring, reduce confidence more
            multiplier *= 0.97
        
        description = (
            f"{weather.get('temp')}°F, Wind {weather.get('wind_speed')}mph" 
            if weather.get('temp') and weather.get('wind_speed') 
            else "Weather checked"
        )
        
        return {
            "is_harsh": is_harsh,
            "confidence_multiplier": multiplier,
            "description": description,
            "temp": weather.get("temp"),
            "wind_speed": weather.get("wind_speed"),
            "precipitation": weather.get("precipitation")
        }