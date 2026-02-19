"""
Recommendations Engine — COMPLETE with Enhanced Parlays
Supports 2, 3, 4, 5, 7, and 12-leg parlays with smart filtering
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.game import Game
from ...models.games_results import GameResult
from ...models.games_upcoming import GameUpcoming
from ...models.injury import Injury

logger = logging.getLogger(__name__)

try:
    from .models_aggregator import ModelsAggregator
except Exception:
    ModelsAggregator = None

try:
    from .value_calculator import ValueCalculator
except Exception:
    ValueCalculator = None

try:
    from .kelly_calculator import KellyCalculator
except Exception:
    KellyCalculator = None


@dataclass
class BettingRecommendation:
    game_id:             str
    pick:                str
    sport:               str
    home_team:           str
    away_team:           str
    start_time:          Optional[datetime]
    confidence:          float
    combined_confidence: float
    edge:                float
    recommended_odds:    float
    fair_odds:           float
    market_odds:         Optional[float]
    ev_percent:          float
    kelly_fraction:      float
    kelly_stake:         Optional[float]
    models_breakdown:    Dict[str, float]
    risk_factors:        List[Dict[str, Any]]
    reason:              str
    bet_type:            str
    has_market_odds:     bool = False
    pick_team_form:      Optional[Dict[str, Any]] = None
    opponent_form:       Optional[Dict[str, Any]] = None


class RecommendationsEngine:
    MIN_CONFIDENCE_ODDS = 52.0
    MIN_EDGE_ODDS       = 1.5
    MIN_CONFIDENCE_FORM = 60.0
    MIN_WIN_RATE_DIFF   = 0.05
    MIN_KELLY           = 0.001
    HIGH_CONFIDENCE     = 72.0
    COIN_FLIP_THRESHOLD = 0.02

    def __init__(self, session: AsyncSession, bankroll: float = 1000.0):
        self.session  = session
        self.bankroll = bankroll
        self.models_aggregator = ModelsAggregator(session) if ModelsAggregator else None
        self.value_calculator  = ValueCalculator()         if ValueCalculator  else None
        self.kelly_calculator  = KellyCalculator()         if KellyCalculator  else None

    async def get_todays_recommendations(
        self,
        models:         Optional[List[str]] = None,
        min_confidence: Optional[float]     = None,
        sports:         Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if min_confidence is None:
            min_confidence = self.MIN_CONFIDENCE_ODDS

        start = datetime.now(timezone.utc)
        games = await self._get_todays_games(sports)
        logger.info(f"Found {len(games)} games to analyze")

        if not games:
            return {"singles": [], "parlays": {},
                    "summary": {"games_analyzed": 0, "recommendations": 0,
                                "message": "No upcoming games found"}}

        all_recs: List[BettingRecommendation] = []
        skipped_coinflip = skipped_no_edge = skipped_no_form = skipped_kelly = 0

        for g in games:
            try:
                recs, reasons = await self._analyze_game_debug(g, models)
                all_recs.extend(recs)
                skipped_coinflip += reasons["coinflip"]
                skipped_no_edge  += reasons["no_edge"]
                skipped_no_form  += reasons["no_form"]
                skipped_kelly    += reasons["kelly"]
            except Exception as exc:
                logger.warning(f"Error analyzing {g.get('game_id')}: {exc}", exc_info=True)

        logger.info(
            f"Analysis complete — {len(all_recs)} raw picks | "
            f"dropped: {skipped_coinflip} coin-flip, {skipped_no_edge} no-edge, "
            f"{skipped_no_form} no-form-adv, {skipped_kelly} low-kelly"
        )

        quality = [
            r for r in all_recs
            if (r.has_market_odds and r.combined_confidence >= min_confidence
                                  and r.edge >= self.MIN_EDGE_ODDS)
            or (not r.has_market_odds and r.combined_confidence >= self.MIN_CONFIDENCE_FORM)
        ]
        quality.sort(
            key=lambda r: r.combined_confidence * max(r.edge, 1),
            reverse=True,
        )

        logger.info(f"After quality filter: {len(quality)} picks")

        # ── Enhanced parlay generation ──────────────────────────────────────
        parlays = self._generate_parlays(quality)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        # Count total parlays across all sizes
        total_parlays = sum(len(parlays_list) for parlays_list in parlays.values())

        return {
            "singles": [self._to_dict(r) for r in quality],
            "parlays": parlays,  # Now a dict with keys like "2_leg", "3_leg", etc.
            "upcoming_games": games,
            "summary": {
                "games_analyzed":     len(games),
                "recommendations":    len(quality),
                "parlays_generated":  total_parlays,
                "parlay_sizes":       list(parlays.keys()),
                "with_market_odds":   sum(1 for r in quality if r.has_market_odds),
                "form_only":          sum(1 for r in quality if not r.has_market_odds),
                "high_confidence":    sum(1 for r in quality if r.combined_confidence >= self.HIGH_CONFIDENCE),
                "elapsed_seconds":    round(elapsed, 2),
                "timestamp":          start.isoformat(),
                "debug": {
                    "dropped_coinflip": skipped_coinflip,
                    "dropped_no_edge":  skipped_no_edge,
                    "dropped_no_form":  skipped_no_form,
                    "dropped_kelly":    skipped_kelly,
                }
            },
        }

    async def _get_todays_games(self, sports: Optional[List[str]]) -> List[Dict[str, Any]]:
        from datetime import datetime, timezone
        # Use timezone-naive UTC datetime for comparison
        now = datetime.utcnow()
        stmt = select(GameUpcoming).where(GameUpcoming.start_time >= now)
        if sports:
            stmt = stmt.where(GameUpcoming.sport.in_(sports))

        rows = (await self.session.execute(stmt)).scalars().all()
        games = [
            {
                "game_id":        g.game_id,
                "sport":          g.sport,
                "home_team_name": g.home_team_name,
                "away_team_name": g.away_team_name,
                "home_team_id":   getattr(g, "home_team_id",  None),
                "away_team_id":   getattr(g, "away_team_id",  None),
                "start_time":     g.start_time,
                "odds_home":      getattr(g, "odds_home",     None),
                "odds_away":      getattr(g, "odds_away",     None),
                "spread_home":    getattr(g, "spread_home",   None),
                "total":          getattr(g, "total",         None),
            }
            for g in rows
        ]

        logger.info(f"✅ Found {len(games)} upcoming games")
        if games:
            sample = [f"{g['away_team_name']} @ {g['home_team_name']}" for g in games[:3]]
            logger.info(f"   First 3: {sample}")

        odds_count = sum(1 for g in games if g.get("odds_home"))
        logger.info(f"   Games with odds: {odds_count}/{len(games)}")
        return games

    async def _analyze_game_debug(
        self,
        game:   Dict[str, Any],
        models: Optional[List[str]],
    ) -> Tuple[List[BettingRecommendation], Dict[str, int]]:
        counts = {"coinflip": 0, "no_edge": 0, "no_form": 0, "kelly": 0}
        recs   = []

        ctx = await self._build_context(game)

        for is_home in (True, False):
            rec, drop_reason = await self._analyze_side(game, is_home, ctx, models)
            if rec:
                recs.append(rec)
            elif drop_reason:
                counts[drop_reason] += 1

        return recs, counts

    async def _analyze_side(
        self,
        game:    Dict[str, Any],
        is_home: bool,
        ctx:     Dict[str, Any],
        models:  Optional[List[str]],
    ) -> Tuple[Optional[BettingRecommendation], Optional[str]]:
        team = game["home_team_name"] if is_home else game["away_team_name"]

        if self.models_aggregator:
            try:
                probs = await self.models_aggregator.get_win_probability(
                    game_data=game, team_name=team,
                    is_home=is_home, context=ctx, models=models,
                )
            except Exception:
                probs = self._fallback_probs(game, is_home, ctx)
        else:
            probs = self._fallback_probs(game, is_home, ctx)

        p    = probs.get("consensus", 0.5)
        conf = probs.get("confidence", 50.0)

        if abs(p - 0.5) < self.COIN_FLIP_THRESHOLD:
            return None, "coinflip"

        raw_ml       = game.get("odds_home" if is_home else "odds_away")
        has_mkt_odds = raw_ml is not None
        mkt_dec      = self._ml_to_dec(raw_ml) if has_mkt_odds else None
        mkt_prob     = (1 / mkt_dec) if mkt_dec else None

        if has_mkt_odds and mkt_prob:
            if self.value_calculator:
                try:
                    val = self.value_calculator.calculate_value(
                        model_probability=p,
                        market_probability=mkt_prob,
                        model_confidence=conf,
                    )
                except Exception:
                    edge = (p - mkt_prob) * 100
                    val  = {"edge_percent": edge, "ev_percent": edge * 1.8}
            else:
                edge = (p - mkt_prob) * 100
                val  = {"edge_percent": edge, "ev_percent": edge * 1.8}

            edge      = val.get("edge_percent", 0)
            ev        = val.get("ev_percent", 0)
            fair_odds = 1 / p
            bet_odds  = mkt_dec

            if edge < self.MIN_EDGE_ODDS:
                return None, "no_edge"

        else:
            form_team = ctx.get("home_form" if is_home else "away_form", {})
            form_opp  = ctx.get("away_form" if is_home else "home_form", {})
            wr_team   = form_team.get("win_rate", 0.5)
            wr_opp    = form_opp.get("win_rate", 0.5)
            gp_team   = form_team.get("games_played", 0)
            gp_opp    = form_opp.get("games_played", 0)

            if gp_team == 0 and gp_opp == 0:
                wr_team = 0.58 if is_home else 0.42
                wr_opp  = 0.42 if is_home else 0.58

            diff = wr_team - wr_opp
            if diff < self.MIN_WIN_RATE_DIFF:
                return None, "no_form"

            form_boost = min(18.0, diff * 100)
            conf       = min(82.0, conf + form_boost)

            edge      = diff * 50
            ev        = 0.0
            fair_odds = 1 / max(p, 0.01)
            bet_odds  = fair_odds

        if self.kelly_calculator:
            try:
                if bet_odds is not None:
                    kelly = self.kelly_calculator.calculate_kelly(
                        probability=p, decimal_odds=bet_odds, fractional_kelly=0.25,
                    )
                else:
                    kelly = 0.0
            except Exception:
                kelly = self._simple_kelly(p, bet_odds if bet_odds is not None else 0.0)
        else:
            kelly = self._simple_kelly(p, bet_odds if bet_odds is not None else 0.0)

        if kelly < self.MIN_KELLY:
            return None, "kelly"

        risks    = await self._assess_risks(game, is_home)
        mult     = math.prod(r["impact"] for r in risks) if risks else 1.0
        adj_conf = min(99.0, conf * mult)

        rec = BettingRecommendation(
            game_id             = game["game_id"],
            pick                = f"{team} ML",
            sport               = game["sport"],
            home_team           = game["home_team_name"],
            away_team           = game["away_team_name"],
            start_time          = game.get("start_time"),
            confidence          = round(conf, 1),
            combined_confidence = round(adj_conf, 1),
            edge                = round(edge, 2),
            recommended_odds    = round(fair_odds, 3),
            fair_odds           = round(fair_odds, 3),
            market_odds         = round(mkt_dec, 3) if mkt_dec else None,
            ev_percent          = round(ev, 2),
            kelly_fraction      = round(kelly, 4),
            kelly_stake         = round(kelly * self.bankroll, 2),
            models_breakdown    = probs.get("breakdown", {}),
            risk_factors        = risks,
            reason              = self._reason(probs, edge, ev, risks, team, has_mkt_odds),
            bet_type            = "moneyline",
            has_market_odds     = has_mkt_odds,
            pick_team_form      = ctx.get("home_form" if is_home else "away_form"),
            opponent_form       = ctx.get("away_form" if is_home else "home_form"),
        )
        return rec, None

    async def _build_context(self, game: Dict[str, Any]) -> Dict[str, Any]:
        ctx = {}
        if game.get("home_team_id"):
            ctx["home_form"] = await self._team_form(game["home_team_id"], game["sport"])
        if game.get("away_team_id"):
            ctx["away_form"] = await self._team_form(game["away_team_id"], game["sport"])
        return ctx

    async def _team_form(self, team_id: str, sport: str, n: int = 10) -> Dict[str, Any]:
        try:
            try:
                order_col = GameResult.game_date
            except AttributeError:
                order_col = GameResult.start_time

            stmt = (
                select(GameResult)
                .where(or_(GameResult.home_team_id == team_id,
                           GameResult.away_team_id == team_id))
                .where(GameResult.sport == sport)
                .order_by(order_col.desc())
                .limit(n)
            )
            rows = (await self.session.execute(stmt)).scalars().all()
        except Exception:
            return {"games_played": 0, "win_rate": 0.5}

        if not rows:
            return {"games_played": 0, "win_rate": 0.5}

        wins = pts_f = pts_a = 0
        for g in rows:
            home  = g.home_team_id == team_id
            ts    = (g.home_score or 0) if home else (g.away_score or 0)
            os_   = (g.away_score or 0) if home else (g.home_score or 0)
            wins += int(ts > os_)
            pts_f += ts
            pts_a += os_

        nn = len(rows)
        return {
            "games_played":       nn,
            "wins":               wins,
            "losses":             nn - wins,
            "win_rate":           wins / nn,
            "avg_points_for":     pts_f  / nn,
            "avg_points_against": pts_a  / nn,
            "point_differential": (pts_f - pts_a) / nn,
        }

    async def _assess_risks(self, game: Dict, is_home: bool) -> List[Dict]:
        risks = []
        tid   = game.get("home_team_id" if is_home else "away_team_id")
        if tid:
            inj = await self._injury_impact(tid)
            if inj["severity"] != "none":
                risks.append({"type": "injury", **inj})
        return risks

    async def _injury_impact(self, team_id: str) -> Dict:
        try:
            rows = (await self.session.execute(
                select(Injury).where(Injury.team_id == team_id)
            )).scalars().all()
        except Exception:
            return {"severity": "none", "confidence_multiplier": 1.0, "impact": 1.0,
                    "description": "Injury data unavailable"}

        if not rows:
            return {"severity": "none", "confidence_multiplier": 1.0, "impact": 1.0,
                    "description": "No injuries"}
        serious = sum(1 for i in rows if i.status in ("Out", "Doubtful"))
        if serious == 0:
            return {"severity": "low",    "confidence_multiplier": 0.98, "impact": 0.98,
                    "description": "Minor injuries only"}
        elif serious == 1:
            return {"severity": "medium", "confidence_multiplier": 0.95, "impact": 0.95,
                    "description": "1 key player out"}
        return {"severity": "high", "confidence_multiplier": 0.88, "impact": 0.88,
                "description": f"{serious} key players out"}

    # ── ENHANCED PARLAY GENERATION ───────────────────────────────────────────

    def _generate_parlays(
        self, singles: List[BettingRecommendation], min_leg_conf: float = 63.0,
    ) -> Dict[str, List[Dict]]:
        """
        Generate parlays of multiple sizes (2, 3, 4, 5, 7, 12 legs).
        
        Returns:
            Dict with keys like "2_leg", "3_leg", etc., containing parlay lists
        """
        if len(singles) < 2:
            return {}
        
        # Configuration: (leg_count, min_confidence, min_combined_prob, max_show)
        parlay_configs = [
            (2,  63.0, 35.0, 10),
            (3,  65.0, 30.0, 8),
            (4,  67.0, 25.0, 6),
            (5,  68.0, 20.0, 5),
            (7,  70.0, 15.0, 3),
            (12, 72.0, 10.0, 2),
        ]
        
        result = {}
        
        for leg_count, min_conf, min_combined, max_show in parlay_configs:
            candidates = [
                s for s in singles 
                if s.combined_confidence >= min_conf
            ]
            
            if len(candidates) < leg_count:
                continue
            
            parlays = []
            for combo in combinations(candidates, leg_count):
                parlay = self._build_parlay(combo, min_combined_confidence=min_combined)
                if parlay:
                    parlays.append(parlay)
            
            if not parlays:
                continue
            
            parlays.sort(
                key=lambda p: (p.get("ev_percent", 0), p["confidence"]),
                reverse=True
            )
            
            parlays = parlays[:max_show]
            key = f"{leg_count}_leg"
            result[key] = parlays
        
        return result

    def _build_parlay(
        self, 
        legs: Tuple[BettingRecommendation, ...],
        min_combined_confidence: float = 35.0
    ) -> Optional[Dict]:
        """Build a single parlay with enhanced metrics."""
        leg_count = len(legs)
        
        combined_prob = math.prod(l.combined_confidence / 100 for l in legs) * 100
        
        if combined_prob < min_combined_confidence:
            return None
        
        parlay_odds = math.prod(l.market_odds or l.fair_odds for l in legs)
        
        # Calculate EV
        win_prob = combined_prob / 100
        profit_on_win = (parlay_odds - 1) * 100
        loss_on_lose = 100
        ev_dollars = (win_prob * profit_on_win) - ((1 - win_prob) * loss_on_lose)
        ev_percent = (ev_dollars / 100) * 100
        
        # Kelly (very conservative for parlays)
        kelly_frac = self._simple_kelly(win_prob, parlay_odds) * 0.5
        kelly_stake = round(kelly_frac * self.bankroll, 2)
        
        # Risk assessment
        risk = self._assess_parlay_risk(leg_count, combined_prob, ev_percent)
        
        leg_details = [
            {
                "pick": l.pick,
                "game": f"{l.away_team} @ {l.home_team}",
                "sport": l.sport,
                "confidence": round(l.combined_confidence, 1),
                "odds": round(l.market_odds or l.fair_odds, 2),
                "has_market_odds": l.has_market_odds,
                "start_time": l.start_time.isoformat() if l.start_time else None,
            }
            for l in legs
        ]
        
        return {
            "leg_count": leg_count,
            "confidence": round(combined_prob, 2),
            "parlay_odds": round(parlay_odds, 2),
            "parlay_odds_american": self._dec_to_ml(parlay_odds),
            "ev_percent": round(ev_percent, 2),
            "ev_dollars": round(ev_dollars, 2),
            "kelly_fraction": round(kelly_frac, 4),
            "kelly_stake": kelly_stake,
            "risk_level": risk,
            "payout_on_100": round((parlay_odds - 1) * 100, 2),
            "legs": leg_details,
        }

    def _assess_parlay_risk(
        self, leg_count: int, combined_prob: float, ev_percent: float
    ) -> Dict[str, Any]:
        """Assess risk level for a parlay."""
        if leg_count >= 10:
            risk, risk_score = "extreme", 100
        elif leg_count >= 7:
            risk, risk_score = "very_high", 80
        elif leg_count >= 5:
            risk, risk_score = "high", 60
        elif leg_count >= 3:
            risk, risk_score = "medium", 40
        else:
            risk, risk_score = "low", 20
        
        if combined_prob < 10:
            risk_score += 20
            if risk not in ["extreme", "very_high"]:
                risk = "very_high"
        elif combined_prob > 40:
            risk_score -= 10
        
        if ev_percent < -20:
            risk_score += 15
        elif ev_percent > 10:
            risk_score -= 10
        
        warnings = []
        if leg_count >= 7:
            warnings.append(f"{leg_count}-leg parlays are extremely difficult to hit")
        if combined_prob < 15:
            warnings.append(f"Only {combined_prob:.1f}% chance of hitting")
        if ev_percent < 0:
            warnings.append(f"Negative expected value ({ev_percent:.1f}%)")
        if leg_count >= 5 and combined_prob < 20:
            warnings.append("Consider smaller parlays for better hit rate")
        
        recommendation = {
            "extreme": "For entertainment only - not recommended for serious bankroll",
            "very_high": "Lottery ticket - bet very small amounts only",
            "high": "Risky but possible - limit stake to <1% bankroll",
            "medium": "Reasonable parlay - use fractional Kelly sizing",
            "low": "Lower risk - standard Kelly sizing appropriate",
        }.get(risk, "")
        
        return {
            "level": risk,
            "score": min(100, max(0, risk_score)),
            "warnings": warnings,
            "recommendation": recommendation
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fallback_probs(self, game: Dict, is_home: bool, ctx: Dict) -> Dict:
        hf   = ctx.get("home_form", {})
        af   = ctx.get("away_form", {})
        hgp  = hf.get("games_played", 0)
        agp  = af.get("games_played", 0)
        hwr  = hf.get("win_rate", 0.58)
        awr  = af.get("win_rate", 0.42)

        if hgp > 0 and agp > 0:
            den   = hwr + awr or 1.0
            form_p = hwr / den if is_home else awr / den
            base  = 0.58 if is_home else 0.42
            p     = form_p * 0.60 + base * 0.40
        else:
            p = 0.58 if is_home else 0.42

        conf = 53.0 + (hgp + agp) * 0.3
        conf = min(65.0, conf)

        return {
            "consensus":  round(p, 3),
            "confidence": round(conf, 1),
            "breakdown":  {
                "home_form":      round(hwr, 3),
                "away_form":      round(awr, 3),
                "home_advantage": 0.58 if is_home else 0.42,
                "games_used":     hgp + agp,
            }
        }

    def _simple_kelly(self, p: float, dec_odds: float) -> float:
        b = dec_odds - 1
        if b <= 0:
            return 0.0
        kelly = max(0.0, ((b * p) - (1 - p)) / b) * 0.25
        return min(0.10, kelly)

    def _reason(self, probs: Dict, edge: float, ev: float,
                risks: List[Dict], team: str, has_odds: bool) -> str:
        parts = []
        conf  = probs.get("confidence", 50)
        gp    = probs.get("breakdown", {}).get("games_used", 0)

        if has_odds:
            level = "Strong" if conf >= 68 else "Moderate"
            parts.append(f"{level} model consensus ({conf:.0f}%)")
            if edge >= 4:
                parts.append(f"excellent edge ({edge:.1f}%)")
            elif edge >= 1.5:
                parts.append(f"positive edge ({edge:.1f}%)")
            if ev > 0:
                parts.append(f"EV +{ev:.1f}%")
        else:
            parts.append(f"Home advantage & form pick ({conf:.0f}% conf)")
            if gp:
                parts.append(f"{gp} games of history")
            parts.append("no market odds available")

        if any(r["severity"] == "high" for r in risks):
            parts.append("⚠️ injury concerns")
        return "; ".join(parts)

    def _to_dict(self, r: BettingRecommendation) -> Dict:
        return {
            "game_id":             r.game_id,
            "pick":                r.pick,
            "sport":               r.sport,
            "home":                r.home_team,
            "away":                r.away_team,
            "start_time":          r.start_time.isoformat() if r.start_time else None,
            "confidence":          r.confidence,
            "combined_confidence": r.combined_confidence,
            "edge":                r.edge,
            "odds":                r.recommended_odds,
            "market_odds":         r.market_odds,
            "has_market_odds":     r.has_market_odds,
            "kelly_fraction":      r.kelly_fraction,
            "kelly_stake":         r.kelly_stake,
            "ev_percent":          r.ev_percent,
            "reason":              r.reason,
            "models":              r.models_breakdown,
            "risk_factors":        r.risk_factors,
        }

    @staticmethod
    def _ml_to_dec(ml: float) -> float:
        return (ml / 100 + 1) if ml > 0 else (100 / abs(ml) + 1)

    @staticmethod
    def _dec_to_ml(dec: float) -> int:
        return int((dec - 1) * 100) if dec >= 2.0 else int(-100 / (dec - 1))