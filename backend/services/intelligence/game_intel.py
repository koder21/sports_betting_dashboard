from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...repositories.game_repo import GameRepository
from ...repositories.player_stat_repo import PlayerStatRepository
from ...repositories.player_repo import PlayerRepository
from ...repositories.team_repo import TeamRepository
from ...models.games_live import GameLive
from ...models.games_results import GameResult
from ...utils.json import to_primitive


class GameIntelligenceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.games = GameRepository(session)
        self.stats = PlayerStatRepository(session)
        self.players = PlayerRepository(session)
        self.teams = TeamRepository(session)

    async def get_game_intel(self, game_id: str) -> Optional[Dict[str, Any]]:
        game = await self.games.get(game_id)
        if not game:
            return None

        live = await self._get_live_game(game_id)
        result = await self._get_result_game(game_id)

        home_team = await self.teams.get(game.home_team_id) if game.home_team_id else None
        away_team = await self.teams.get(game.away_team_id) if game.away_team_id else None

        home_players: List = []
        away_players: List = []
        if home_team:
            home_players = list(await self.players.list_by_team(home_team.team_id))
        if away_team:
            away_players = list(await self.players.list_by_team(away_team.team_id))

        home_stats = []
        for p in home_players:
            ps = await self.stats.get_for_player_game(p.player_id, game.game_id)
            if ps:
                home_stats.append({
                    "player": p.full_name or p.name or p.player_id,
                    "stats": getattr(ps, "stats_json", None) or _stat_row_to_dict(ps),
                })

        away_stats = []
        for p in away_players:
            ps = await self.stats.get_for_player_game(p.player_id, game.game_id)
            if ps:
                away_stats.append({
                    "player": p.full_name or p.name or p.player_id,
                    "stats": getattr(ps, "stats_json", None) or _stat_row_to_dict(ps),
                })

        status = live.status if live and live.status else (game.status or (result.status if result else None))

        return to_primitive({
            "game_id": game.game_id,
            "sport_id": game.sport_id,
            "sport": game.sport,
            "league": game.league,
            "start_time": game.start_time,
            "status": status,
            "home_team": home_team.name if home_team else None,
            "away_team": away_team.name if away_team else None,
            "home_stats": home_stats,
            "away_stats": away_stats,
            "boxscore": game.boxscore_json,
            "play_by_play": game.play_by_play_json,
            "game": {
                "home_team_name": game.home_team_name,
                "away_team_name": game.away_team_name,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "period": game.period,
                "clock": game.clock,
                "venue": game.venue,
            },
            "live": {
                "home_team_name": live.home_team_name,
                "away_team_name": live.away_team_name,
                "home_score": live.home_score,
                "away_score": live.away_score,
                "period": live.period,
                "clock": live.clock,
                "status": live.status,
            } if live else None,
            "result": {
                "home_team_name": result.home_team_name,
                "away_team_name": result.away_team_name,
                "home_score": result.home_score,
                "away_score": result.away_score,
                "status": result.status,
            } if result else None,
        })

    async def _get_live_game(self, game_id: str) -> Optional[GameLive]:
        result = await self.session.execute(
            select(GameLive).where(GameLive.game_id == game_id)
        )
        return result.scalar_one_or_none()

    async def _get_result_game(self, game_id: str) -> Optional[GameResult]:
        result = await self.session.execute(
            select(GameResult).where(GameResult.game_id == game_id)
        )
        return result.scalar_one_or_none()


def _stat_row_to_dict(ps: Any) -> dict:
    """Turn a PlayerStats row into a dict for grading (e.g. points, rebounds)."""
    return {c.key: getattr(ps, c.key) for c in ps.__table__.columns if hasattr(ps, c.key)}
