from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..espn_client import ESPNClient, SPORT_CONFIG, BASE_SITE, BASE_CORE, BASE_CDN
from ..alerts import send_email_alert
from ...repositories.teams import TeamRepository
from ...repositories.games import GameRepository
from ...repositories.players import PlayerRepository
from ...repositories.injuries import InjuryRepository
from ...models.alert import Alert
from ...models import Standing, Team
from ...utils import safe_sleep, safe_get


class TeamLeagueScraper:
    def __init__(self, session: AsyncSession, client: ESPNClient, sport_name: str, league: Optional[str] = None):
        self.session = session
        self.client = client
        self.sport_name = sport_name
        self.league = league

    async def scrape(self) -> None:
        config = SPORT_CONFIG[self.sport_name]
        path = config["path"]
        full_path = f"{path}/{self.league}" if self.league else path

        team_repo = TeamRepository(self.session)
        game_repo = GameRepository(self.session)
        player_repo = PlayerRepository(self.session)
        injury_repo = InjuryRepository(self.session)

        sport = await team_repo.get_or_create_sport(self.sport_name, self.league)

        # Teams
        teams_url = f"{BASE_SITE}{full_path}/teams"
        teams_resp = await self.client.get_json(teams_url)
        teams_list = safe_get(teams_resp or {}, ["sports", 0, "leagues", 0, "teams"], []) or []
        for item in teams_list:
            team_data = item.get("team", {})
            espn_id = team_data.get("id")
            name = team_data.get("displayName")
            if not espn_id or not name:
                continue
            stats_url = f"{BASE_CORE}{full_path}/seasons/{datetime.utcnow().year}/types/2/teams/{espn_id}/statistics"
            stats = await self.client.get_json(stats_url)
            record = safe_get(stats, ["record", "items", 0, "displayValue"], "")
            await team_repo.upsert(
                espn_id=espn_id,
                name=name,
                sport_id=sport.id,
                record=record,
                stats_json=stats,
            )
            await safe_sleep(0.1)

        await self.session.flush()

        # Standings
        standings_url = f"{BASE_SITE}{full_path}/standings"
        standings = await self.client.get_json(standings_url)
        children = (standings or {}).get("children", [])
        for entry in children:
            for standing in entry.get("standings", {}).get("entries", []):
                team_id = standing.get("team", {}).get("id")
                if not team_id:
                    continue
                team = await team_repo.get_by_espn_id(str(team_id))
                if not team:
                    continue
                rank = standing.get("rank")
                rec = safe_get(standing, ["stats", 0, "displayValue"], "")
                st = Standing(
                    team_id=team.team_id,
                    rank=rank,
                    record=rec,
                    season_year=datetime.utcnow().year,
                )
                try:
                    self.session.add(st)
                    await self.session.flush()
                except IntegrityError:
                    await self.session.rollback()
        await safe_sleep(0.1)

        # Scoreboard
        start, end = self.client.date_range_params()
        scoreboard_url = f"{BASE_SITE}{full_path}/scoreboard?dates={start}-{end}&limit=1000"
        scoreboard = await self.client.get_json(scoreboard_url)

        if (scoreboard is None or not (scoreboard or {}).get("events")) and config.get("cdn"):
            cdn_sport = config.get("cdn")
            cdn_url = f"{BASE_CDN}/{cdn_sport}/scoreboard?xhr=1"
            cdn_scoreboard = await self.client.get_json(cdn_url)
            if cdn_scoreboard:
                scoreboard = self._convert_cdn_scoreboard(cdn_scoreboard)

        events = (scoreboard or {}).get("events", [])
        for event in events:
            espn_id = event.get("id")
            date_str = event.get("date")
            if not espn_id or not date_str:
                continue
            date = self.client.parse_date(date_str) if date_str else None
            if not date:
                continue
            comps = event.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[-1])

            home_team = await team_repo.get_by_espn_id(str(home.get("id", "") or ""))
            away_team = await team_repo.get_by_espn_id(str(away.get("id", "") or ""))

            # Extract team names and scores from ESPN data
            home_team_name = home.get("team", {}).get("displayName", "Home Team")
            away_team_name = away.get("team", {}).get("displayName", "Away Team")
            home_score = home.get("score")
            away_score = away.get("score")
            
            # Extract period and clock from competition status
            status_obj = comp.get("status", {})
            period = status_obj.get("period")
            clock = status_obj.get("displayClock", "")

            game_data = {
                "espn_id": espn_id,
                "date": date,
                "sport_id": sport.id,
                "home_team_id": home_team.team_id if home_team else None,
                "away_team_id": away_team.team_id if away_team else None,
                "home_team_name": home_team_name,
                "away_team_name": away_team_name,
                "home_score": home_score,
                "away_score": away_score,
                "period": period,
                "clock": clock,
                "venue": safe_get(event, ["venue", "fullName"], ""),
                "status": safe_get(event, ["status", "type", "name"], ""),
                "score": "",
                "lines_json": None,
                "odds_history_json": None,
                "play_by_play_json": None,
                "boxscore_json": None,
                "head_to_head_json": None,
                "season_year": date.year if date else datetime.utcnow().year,
            }

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

            # Odds history (best-effort)
            if getattr(game, "lines_json", None):
                provider_id = (game.lines_json or {}).get("provider", {}).get("id", "38")
                history_url = f"{BASE_CORE}{full_path}/events/{espn_id}/competitions/{espn_id}/odds/{provider_id}/history/0/movement?limit=100"
                try:
                    history = await self.client.get_json(history_url)
                    if history:
                        game.odds_history_json = history
                        await self.session.flush()
                except Exception:
                    pass

            # Summary
            summary_url = f"{BASE_SITE}{full_path}/summary?event={espn_id}"
            try:
                summary = await self.client.get_json(summary_url)
                if summary:
                    game.boxscore_json = (summary or {}).get("boxscore", {})
                    game.play_by_play_json = (summary or {}).get("plays", [])
                    await self.session.flush()
            except Exception:
                pass

            # Head-to-head (best-effort)
            h2h_url = f"{BASE_CORE}{full_path}/events/{espn_id}/competitions/{espn_id}/odds/38/head-to-heads"
            try:
                h2h = await self.client.get_json(h2h_url)
                if h2h:
                    game.head_to_head_json = ((h2h or {}).get("items") or [])[:10]
                    await self.session.flush()
            except Exception:
                pass

            await safe_sleep(0.1)

        # Roster + player stats + injuries
        result = await self.session.execute(select(Team).where(Team.sport_id == sport.id))
        teams_for_sport = result.scalars().all()

        for team in teams_for_sport:
            roster_url = f"{BASE_CORE}{full_path}/teams/{team.team_id}/roster"
            roster = await self.client.get_json(roster_url)
            athletes = (roster or {}).get("athletes", [])
            for group in athletes:
                for entry in group.get("items", []):
                    pid = entry.get("id")
                    name = entry.get("fullName")
                    pos = safe_get(entry, ["position", "abbreviation"], None)
                    ref = entry.get("$ref")
                    if not pid or not name:
                        continue
                    stats_url = f"{BASE_CORE}{full_path}/seasons/{datetime.utcnow().year}/types/2/athletes/{pid}/statistics"
                    stats = await self.client.get_json(stats_url)
                    await player_repo.upsert(
                        espn_id=str(pid),
                        name=name,
                        position=pos,
                        team_id=team.team_id,
                        season_stats_json=stats,
                        espn_ref=ref,
                    )
                    await safe_sleep(0.05)

            # Injuries
            injuries_url = f"{BASE_CORE}{full_path}/teams/{team.team_id}/injuries?limit=100"
            injuries = await self.client.get_json(injuries_url)
            for inj in (injuries or {}).get("items", []):
                athlete_ref = safe_get(inj, ["athlete", "$ref"], "")
                if not athlete_ref:
                    continue
                player_id_str = athlete_ref.rstrip("/").split("/")[-1]
                player = await player_repo.get_by_espn_and_team(player_id_str, team.team_id)
                if not player:
                    continue
                desc = inj.get("longComment", "")
                status = safe_get(inj, ["status", "name"], "")
                await injury_repo.add_if_new(player.player_id, team.team_id, desc, status)
                if "out" in status.lower():
                    send_email_alert(
                        f"Key Injury: {player.name or player.full_name or player.player_id} ({status})",
                        "dakota.nicol@gmail.com",
                    )
            await safe_sleep(0.1)

        await self.session.commit()

    def _convert_cdn_scoreboard(self, cdn_data: dict) -> dict:
        """Convert CDN scoreboard format to site.api format."""
        sb_data = cdn_data.get("content", {}).get("sbData", {})
        events = sb_data.get("events", [])
        for event in events:
            if "id" not in event and "$id" in event:
                event["id"] = event.get("$id")
        return {"events": events}