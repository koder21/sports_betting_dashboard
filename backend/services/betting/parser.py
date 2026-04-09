import re
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...repositories.sport_repo import SportRepository
from ...repositories.game_repo import GameRepository
from ...repositories.player_repo import PlayerRepository
from ...models.sport import Sport
from ...services.espn_client import ESPNClient


class BetParser:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.sports = SportRepository(session)
        self.games = GameRepository(session)
        self.players = PlayerRepository(session)
        self.espn_client = ESPNClient()

    async def parse_multiple(self, text: str) -> List[Dict[str, Any]]:
        """Parse multiple parlays and singles from text format"""
        bets = []

        # First, split by 'Type:' to handle cases where bets are concatenated without newlines
        # This is a preprocessing step before splitting by newlines
        text = re.sub(
            r"(\.)(?=Type:)", r"\1\n", text
        )  # Add newline before 'Type:' if missing

        lines = text.strip().split("\n")

        current_parlay: list[Any] = []
        current_parlay_name = None
        current_parlay_explicit = False
        parlay_counter = 1

        for line in lines:
            line = line.strip()
            if not line:
                # Blank line indicates end of a parlay/group
                if current_parlay:
                    bets.extend(current_parlay)
                    current_parlay = []
                    current_parlay_name = None
                    current_parlay_explicit = False
                continue

            # Check for explicit parlay header
            if line.lower().startswith("parlay #") or line.lower().startswith(
                "singles"
            ):
                if current_parlay:
                    bets.extend(current_parlay)
                current_parlay = []
                current_parlay_name = line
                current_parlay_explicit = True
                continue

            # Check for leg line
            if "type:" in line.lower():
                # Always use the most recent explicit parlay/singles header as the group name
                if current_parlay_name is None:
                    current_parlay_name = f"Parlay #{parlay_counter}"
                    current_parlay_explicit = False
                    parlay_counter += 1
                leg = await self._parse_leg(line, current_parlay_name)
                if leg:
                    current_parlay.append(leg)

        # Don't forget the last parlay
        if current_parlay:
            bets.extend(current_parlay)

        return bets

    async def _parse_leg(
        self, line: str, parlay_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse a single leg from a line"""
        parsed: Dict[str, Any] = {}

        # Extract fields using regex
        sport_match = re.search(r"sport:\s*([a-zA-Z0-9_.-]+)", line, re.IGNORECASE)
        type_match = re.search(r"type:\s*(\w+)", line, re.IGNORECASE)
        selection_match = re.search(r"selection:\s*([^,]+)", line, re.IGNORECASE)
        game_match = re.search(r"game:\s*([^,]+)", line, re.IGNORECASE)
        date_match = re.search(r"date:\s*(\d{4}-\d{2}-\d{2})", line, re.IGNORECASE)
        game_id_match = re.search(r"game\s+id:\s*(\d+)", line, re.IGNORECASE)
        odds_match = re.search(r"odds:\s*([+-]?\d+\.?\d*)", line, re.IGNORECASE)
        stake_match = re.search(r"stake:\s*([\d.]+)", line, re.IGNORECASE)
        reason_match = re.search(r"reason:\s*(.+)$", line, re.IGNORECASE)

        if not type_match or not selection_match:
            return None

        bet_type = type_match.group(1).lower()
        selection = selection_match.group(1).strip()
        game_str = game_match.group(1).strip() if game_match else None
        date_str = date_match.group(1) if date_match else None
        game_id = game_id_match.group(1) if game_id_match else None
        odds = float(odds_match.group(1)) if odds_match else -110
        stake = float(stake_match.group(1)) if stake_match else 100
        reason = reason_match.group(1).strip() if reason_match else None

        # Improved bet type detection
        selection_lower = selection.lower()
        team_total_pattern = re.match(
            r"^[a-zA-Z\s]+/[a-zA-Z\s]+\s+(over|under)\s+\d+", selection
        )
        player_prop_pattern = re.match(
            r"^[a-zA-Z\s\.'-]+\s+(over|under)\s+\d+", selection
        )
        spread_pattern = re.match(r"^[a-zA-Z\s]+[\s-]+[+\-]?\d+\.?\d*$", selection)

        if " ml" in selection_lower or " moneyline" in selection_lower:
            bet_type = "moneyline"
        elif team_total_pattern:
            bet_type = "total"
        elif player_prop_pattern:
            bet_type = "prop"
        elif spread_pattern:
            bet_type = "spread"
        elif "over" in selection_lower or "under" in selection_lower:
            bet_type = "total"

        # Use explicit sport if present, otherwise fall back to detection
        sport = None
        if sport_match:
            sport_str = sport_match.group(1).strip().lower()
            # Try league code first, then name
            sport = await self.sports.get_by_league_code(sport_str)
            if not sport:
                # Try by name (e.g., 'nba', 'nfl', 'mlb', etc.)
                from ...models.sport import Sport as SportModel

                stmt = select(SportModel).where(SportModel.name.ilike(sport_str))
                result = await self.session.execute(stmt)
                sport = result.scalar_one_or_none()
        if not sport:
            sport = await self._detect_sport(game_str, selection)
        if not sport:
            return None

        parsed["sport_id"] = sport.id
        parsed["bet_type"] = bet_type
        parsed["selection"] = selection
        parsed["game_str"] = game_str
        parsed["date_str"] = date_str
        parsed["odds"] = odds
        parsed["stake"] = stake
        parsed["reason"] = reason
        parsed["parlay_name"] = parlay_name
        parsed["raw_text"] = line

        # Additional parsing for prop bets
        if bet_type.lower() == "prop" or bet_type.lower() == "total":
            await self._parse_prop(parsed, selection)

        # Find game_id - use provided game_id first, otherwise look it up
        if game_id:
            # Game ID was provided directly
            parsed["game_id"] = game_id
        elif game_str:
            # Need to look up the game
            game = await self._find_game(game_str, date_str, sport.id)
            if game:
                parsed["game_id"] = game.game_id

        return parsed

    async def _parse_prop(self, parsed: Dict, selection: str) -> None:
        """Extract prop market and line from selection"""
        selection_lower = selection.lower()

        if "over" in selection_lower:
            parsed["market"] = "over"
        elif "under" in selection_lower:
            parsed["market"] = "under"

        # Extract stat type
        if "pts" in selection_lower or "points" in selection_lower:
            parsed["stat_type"] = "points"
        elif "rebounds" in selection_lower or "reb" in selection_lower:
            parsed["stat_type"] = "rebounds"
        elif "assists" in selection_lower or "ast" in selection_lower:
            parsed["stat_type"] = "assists"
        elif "yards" in selection_lower:
            parsed["stat_type"] = (
                "passing_yards" if "pass" in selection_lower else "rushing_yards"
            )

        # Extract player name
        # Extract player name: everything before ' over ' or ' under '
        player_match = re.search(
            r"^(.+?)\s+(?:over|under)\s+[\d.]+", selection, re.IGNORECASE
        )
        if player_match:
            player_name = player_match.group(1).strip()
            # Try to find player
            player = await self.players.search_by_name(player_name)
            if player:
                # If player is a list or sequence, take the first match
                first_player = (
                    player[0] if isinstance(player, (list, tuple)) else player
                )
                parsed["player_id"] = getattr(first_player, "player_id", None)
                parsed["player_name"] = getattr(
                    first_player, "full_name", None
                ) or getattr(first_player, "player_name", None)
            else:
                parsed["player_name"] = player_name

    async def _detect_sport(
        self, game_str: Optional[str] = None, selection: Optional[str] = None
    ) -> Optional[Any]:
        """Detect sport from game or selection text by querying real teams from DB"""
        search_text = ((game_str or "") + " " + (selection or "")).lower()

        # Fetch all teams from database
        from ...models.team import Team
        from ...models.sport import Sport

        # Get team names grouped by sport
        stmt = select(Team.name, Sport.league_code).join(
            Sport, Team.sport_id == Sport.id
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Build dict: league_code -> set of team names
        teams_by_sport: dict = {}
        for team_name, league_code in rows:
            if team_name and league_code:
                teams_by_sport.setdefault(league_code, set()).add(team_name.lower())

        # Also check games table for team names
        from ...models.game import Game

        game_stmt = select(Game.home_team_name, Game.away_team_name, Game.league).where(
            Game.home_team_name.isnot(None)
        )
        game_result = await self.session.execute(game_stmt)
        for home, away, league in game_result.all():
            if home and league:
                teams_by_sport.setdefault(league, set()).add(home.lower())
            if away and league:
                teams_by_sport.setdefault(league, set()).add(away.lower())

        # Also check games_live table
        from ...models.games_live import GameLive

        live_stmt = select(
            GameLive.home_team_name, GameLive.away_team_name, GameLive.sport
        ).where(GameLive.home_team_name.isnot(None))
        live_result = await self.session.execute(live_stmt)
        for home, away, sport in live_result.all():
            if home and sport:
                teams_by_sport.setdefault(sport, set()).add(home.lower())
            if away and sport:
                teams_by_sport.setdefault(sport, set()).add(away.lower())

        # Also check games_upcoming table
        from ...models.games_upcoming import GameUpcoming

        upcoming_stmt = select(
            GameUpcoming.home_team_name, GameUpcoming.away_team_name, GameUpcoming.sport
        ).where(GameUpcoming.home_team_name.isnot(None))
        upcoming_result = await self.session.execute(upcoming_stmt)
        for home, away, sport in upcoming_result.all():
            if home and sport:
                teams_by_sport.setdefault(sport, set()).add(home.lower())
            if away and sport:
                teams_by_sport.setdefault(sport, set()).add(away.lower())

        # Try to match search text against teams
        for league_code, team_names in teams_by_sport.items():
            if any(team in search_text for team in team_names):
                return await self.sports.get_by_league_code(league_code)

        return None

    async def _find_game(
        self,
        game_str: str,
        date_str: Optional[str] = None,
        sport_id: Optional[int] = None,
    ) -> Optional[Any]:
        """Find a game by team names and date - query database first, then ESPN API"""
        teams = [t.strip() for t in game_str.split("vs")]
        if len(teams) != 2:
            return None

        team1, team2 = teams[0].lower(), teams[1].lower()

        # First, try to find in local database
        games = await self.games.list()

        for game in games:
            home = (game.home_team_name or "").lower()
            away = (game.away_team_name or "").lower()

            # Check if teams match (both orderings)
            home_match = team1 in home or home in team1
            away_match = team2 in away or away in team2

            reverse_home_match = team2 in home or home in team2
            reverse_away_match = team1 in away or away in team1

            teams_match = (home_match and away_match) or (
                reverse_home_match and reverse_away_match
            )

            if teams_match:
                # Check date if provided
                if date_str:
                    if game.start_time:
                        game_date = game.start_time.date()
                        try:
                            import datetime as dt

                            search_date = dt.datetime.strptime(
                                date_str, "%Y-%m-%d"
                            ).date()
                            if game_date != search_date:
                                continue
                        except Exception:
                            pass

                return game

        # If not found in database, query ESPN API
        if sport_id:
            sport = await self.sports.get(sport_id)
            if sport:
                game_from_espn = await self._find_game_in_espn(
                    team1, team2, date_str, sport.name
                )
                if game_from_espn:
                    return game_from_espn

        return None

    async def _find_game_in_espn(
        self,
        team1: str,
        team2: str,
        date_str: Optional[str] = None,
        sport_name: Optional[str] = None,
    ) -> Optional[Dict]:
        """Search ESPN API for a game matching the team names"""
        # Map sport name to ESPN API path
        sport_map = {
            "NBA": ("basketball", "nba"),
            "NCAAB": ("basketball", "mens-college-basketball"),
            "NFL": ("football", "nfl"),
            "NHL": ("hockey", "nhl"),
            "EPL": ("soccer", "eng.1"),
        }

        if not sport_name:
            return None

        api_path = sport_map.get(sport_name.upper())
        if not api_path:
            return None

        sport_type, league = api_path
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_type}/{league}/scoreboard"

        try:
            data = await self.espn_client.get_json(url)
            if not data or "events" not in data:
                return None

            for event in data["events"]:
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])

                home_team = next(
                    (c for c in competitors if c.get("homeAway") == "home"), None
                )
                away_team = next(
                    (c for c in competitors if c.get("homeAway") == "away"), None
                )

                if not home_team or not away_team:
                    continue

                home_name = (home_team.get("team", {}).get("displayName") or "").lower()
                away_name = (away_team.get("team", {}).get("displayName") or "").lower()

                # Check team matches
                team1_match = (
                    team1 in home_name
                    or home_name in team1
                    or team1 in away_name
                    or away_name in team1
                )
                team2_match = (
                    team2 in home_name
                    or home_name in team2
                    or team2 in away_name
                    or away_name in team2
                )

                if not (team1_match and team2_match):
                    continue

                # Check date if provided
                if date_str:
                    try:
                        import datetime as dt

                        game_date_str = event.get("date", "")
                        # Parse ESPN date format (2026-02-07T20:00Z)
                        game_date = dt.datetime.fromisoformat(
                            game_date_str.replace("Z", "+00:00")
                        ).date()
                        search_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                        if game_date != search_date:
                            continue
                    except Exception:
                        pass

                # Return a plain dictionary with the game info
                return {
                    "game_id": event.get("id"),
                    "home_team_name": home_team.get("team", {}).get("displayName"),
                    "away_team_name": away_team.get("team", {}).get("displayName"),
                    "start_time": event.get("date"),
                }

        except Exception as e:
            print(f"Error querying ESPN API: {e}")
            return None

        return None

    async def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Legacy single-bet parser for backward compatibility"""
        t = text.lower()

        sport = None
        if "nba" in t:
            sport = await self.sports.get_by_league_code("nba")
        elif "nfl" in t:
            sport = await self.sports.get_by_league_code("nfl")
        elif "nhl" in t:
            sport = await self.sports.get_by_league_code("nhl")
        elif "mlb" in t:
            sport = await self.sports.get_by_league_code("mlb")

        if not sport:
            return None

        bet_type = None
        market = None
        selection = None

        if "over" in t:
            bet_type = "prop"
            selection = "over"
        elif "under" in t:
            bet_type = "prop"
            selection = "under"
        elif "ml" in t or "moneyline" in t:
            bet_type = "moneyline"
        elif "spread" in t:
            bet_type = "spread"

        if bet_type == "prop":
            if "points" in t:
                market = "points"
            elif "rebounds" in t:
                market = "rebounds"
            elif "assists" in t:
                market = "assists"
            elif "yards" in t:
                market = "yards_pass"

        return {
            "sport_id": sport.id,
            "bet_type": bet_type,
            "market": market,
            "selection": selection,
        }
