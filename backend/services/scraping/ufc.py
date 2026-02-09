from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from .base import BaseScraper
from ..espn_client import ESPNClient, SPORT_CONFIG, BASE_SITE, BASE_CORE, BASE_CDN
from ...repositories.teams import TeamRepository
from ...repositories.games import GameRepository
from ...repositories.players import PlayerRepository
from ...repositories.injuries import InjuryRepository
from ...models import Sport, Game, PlayerStat
from ...utils import safe_sleep, safe_get
from ...models.alert import Alert


class UFCScraper(BaseScraper):
    async def scrape(self) -> None:
        config = SPORT_CONFIG["ufc"]
        path = config["path"]
        full_path = path

        team_repo = TeamRepository(self.session)
        game_repo = GameRepository(self.session)
        player_repo = PlayerRepository(self.session)
        injury_repo = InjuryRepository(self.session)

        sport = await team_repo.get_or_create_sport("ufc", None)

        # UFC uses events directly; scoreboard
        start, end = self.client.date_range_params()
        scoreboard_url = f"{BASE_SITE}{full_path}/scoreboard?dates={start}-{end}&limit=1000"
        scoreboard = await self.client.get_json(scoreboard_url)
        events = (scoreboard or {}).get("events", [])
        # Try CDN if primary fails
        if not events and config.get("cdn"):
            cdn_sport = config.get("cdn")
            cdn_url = f"{BASE_CDN}/{cdn_sport}/scoreboard?xhr=1"
            cdn_scoreboard = await self.client.get_json(cdn_url)
            if cdn_scoreboard:
                converted = self._convert_cdn_scoreboard(cdn_scoreboard)
                events = converted.get("events", [])

        # We'll treat each fighter as a "player" with no team
        for event in events:
            espn_id = event.get("id")
            date_str = event.get("date")
            if not espn_id or not date_str:
                continue
            espn_id = str(espn_id)
            date = self.client.parse_date(date_str)
            comps = event.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            # For UFC, we won't use teams; home/away are just sides
            game_data = {
                "espn_id": espn_id,
                "date": date,
                "home_team_id": None,
                "away_team_id": None,
                "venue": safe_get(event, ["venue", "fullName"], ""),
                "status": safe_get(event, ["status", "type", "name"], ""),
                "score": "",
                "lines_json": None,
                "odds_history_json": None,
                "play_by_play_json": None,
                "boxscore_json": None,
                "head_to_head_json": None,
                "season_year": date.year,
            }

            status = game_data["status"]
            if status in ("STATUS_FINAL", "STATUS_FULL_TIME"):
                # UFC scoring is more complex; we just store winner/loser in score string
                winner = next((c for c in competitors if c.get("winner")), None)
                loser = next((c for c in competitors if not c.get("winner")), None)
                if winner and loser:
                    game_data["score"] = f"{winner.get('displayName')} def. {loser.get('displayName')}"

            if "odds" in comp:
                odds = comp["odds"][0]
                game_data["lines_json"] = odds
            else:
                odds_url = f"{BASE_CORE}{full_path}/events/{espn_id}/competitions/{espn_id}/odds"
                try:
                    odds_resp = await self.client.get_json(odds_url)
                    odds_items = (odds_resp or {}).get("items") or (odds_resp or {}).get("odds") or []
                    if odds_items:
                        game_data["lines_json"] = odds_items[0]
                except Exception:
                    pass

            game = await game_repo.upsert(game_data)

            # Summary
            summary_url = f"{BASE_SITE}{full_path}/summary?event={espn_id}"
            try:
                summary = await self.client.get_json(summary_url)
                if summary:
                    game.boxscore_json = summary.get("boxscore", {})
                    game.play_by_play_json = summary.get("plays", [])
                    await self.session.flush()
            except Exception:
                pass

            await safe_sleep(0.1)

            # Fighters as players
            for fighter in competitors:
                athlete = fighter.get("athlete", {})
                pid = athlete.get("id")
                name = athlete.get("displayName") or athlete.get("fullName")
                ref = athlete.get("$ref")
                if not pid or not name:
                    continue
                pid = str(pid)
                stats_url = f"{BASE_CORE}{full_path}/athletes/{pid}/statistics"
                try:
                    stats = await self.client.get_json(stats_url)
                except Exception:
                    stats = {}
                await player_repo.upsert(
                    espn_id=pid,
                    name=name,
                    position=None,
                    team_id=None,
                    season_stats_json=stats,
                    espn_ref=ref,
                )
                await safe_sleep(0.05)

        await self.session.commit()

    def _convert_cdn_scoreboard(self, cdn_data: dict) -> dict:
        """Convert CDN scoreboard format to site.api format."""
        sb_data = cdn_data.get("content", {}).get("sbData", {})
        events = sb_data.get("events", [])
        for event in events:
            if "id" not in event and "$id" in event:
                event["id"] = event.get("$id")
        return {"events": events}