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
        lines = text.strip().split('\n')
        
        current_parlay = []
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
            if line.lower().startswith('parlay #') or line.lower().startswith('singles'):
                if current_parlay:
                    bets.extend(current_parlay)
                current_parlay = []
                current_parlay_name = line
                current_parlay_explicit = True
                continue
            
            # Check for leg line
            if 'type:' in line.lower():
                # If we don't have a parlay name yet, generate one
                if current_parlay_name is None:
                    current_parlay_name = f"Parlay #{parlay_counter}"
                    current_parlay_explicit = False
                    parlay_counter += 1
                
                leg = await self._parse_leg(line, current_parlay_name)
                if leg:
                    # If grouping was auto and sport changes, start a new group
                    if current_parlay and not current_parlay_explicit:
                        last_sport_id = current_parlay[-1].get("sport_id")
                        if last_sport_id and leg.get("sport_id") and last_sport_id != leg.get("sport_id"):
                            bets.extend(current_parlay)
                            current_parlay = []
                            current_parlay_name = f"Parlay #{parlay_counter}"
                            current_parlay_explicit = False
                            parlay_counter += 1
                            leg["parlay_name"] = current_parlay_name
                    current_parlay.append(leg)
        
        # Don't forget the last parlay
        if current_parlay:
            bets.extend(current_parlay)
        
        return bets

    async def _parse_leg(self, line: str, parlay_name: str = None) -> Optional[Dict[str, Any]]:
        """Parse a single leg from a line"""
        parsed = {}
        
        # Extract fields using regex
        type_match = re.search(r'type:\s*(\w+)', line, re.IGNORECASE)
        selection_match = re.search(r'selection:\s*([^,]+)', line, re.IGNORECASE)
        game_match = re.search(r'game:\s*([^,]+)', line, re.IGNORECASE)
        date_match = re.search(r'date:\s*(\d{4}-\d{2}-\d{2})', line, re.IGNORECASE)
        game_id_match = re.search(r'game\s+id:\s*(\d+)', line, re.IGNORECASE)
        odds_match = re.search(r'odds:\s*([+-]?\d+\.?\d*)', line, re.IGNORECASE)
        stake_match = re.search(r'stake:\s*([\d.]+)', line, re.IGNORECASE)
        reason_match = re.search(r'reason:\s*([^.]+\.?)', line, re.IGNORECASE)
        
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
        
        # Detect sport from game teams or selection
        sport = await self._detect_sport(game_str, selection)
        if not sport:
            return None
        
        parsed['sport_id'] = sport.id
        parsed['bet_type'] = bet_type
        parsed['selection'] = selection
        parsed['game_str'] = game_str
        parsed['date_str'] = date_str
        parsed['odds'] = odds
        parsed['stake'] = stake
        parsed['reason'] = reason
        parsed['parlay_name'] = parlay_name
        parsed['raw_text'] = line
        
        # Additional parsing for prop bets
        if bet_type.lower() == 'prop':
            await self._parse_prop(parsed, selection)
        
        # Find game_id - use provided game_id first, otherwise look it up
        if game_id:
            # Game ID was provided directly
            parsed['game_id'] = game_id
        elif game_str:
            # Need to look up the game
            game = await self._find_game(game_str, date_str, sport.id)
            if game:
                parsed['game_id'] = game.game_id
        
        return parsed

    async def _parse_prop(self, parsed: Dict, selection: str) -> None:
        """Extract prop market and line from selection"""
        selection_lower = selection.lower()
        
        if 'over' in selection_lower:
            parsed['market'] = 'over'
        elif 'under' in selection_lower:
            parsed['market'] = 'under'
        
        # Extract stat type
        if 'pts' in selection_lower or 'points' in selection_lower:
            parsed['stat_type'] = 'points'
        elif 'rebounds' in selection_lower or 'reb' in selection_lower:
            parsed['stat_type'] = 'rebounds'
        elif 'assists' in selection_lower or 'ast' in selection_lower:
            parsed['stat_type'] = 'assists'
        elif 'yards' in selection_lower:
            parsed['stat_type'] = 'passing_yards' if 'pass' in selection_lower else 'rushing_yards'
        
        # Extract player name
        player_match = re.search(r'^([^o].*?)\s+over|\s+under', selection_lower)
        if player_match:
            player_name = player_match.group(1).strip()
            # Try to find player
            player = await self.players.search_by_name(player_name)
            if player:
                parsed['player_id'] = player.player_id
                parsed['player_name'] = player.full_name or player.player_name
            else:
                parsed['player_name'] = player_name

    async def _detect_sport(self, game_str: str = None, selection: str = None) -> Optional[Any]:
        """Detect sport from game or selection text"""
        search_text = (game_str or '') + ' ' + (selection or '')
        search_text = search_text.lower()
        
        # NBA teams
        nba_teams = ['celtics', 'heat', 'bucks', 'pacers', 'timberwolves', 'pelicans',
                     'kings', 'clippers', 'lakers', 'warriors', 'mavericks', 'suns',
                     'nets', 'wizards', 'thunder', 'rockets', 'magic', 'jazz',
                     'hawks', 'hornets', 'cavaliers', 'pistons', 'bulls', 'raptors',
                     'grizzlies', 'nuggets', 'trail blazers', 'blazers', 'spurs',
                     '76ers', 'knicks', 'lions']
        
        # NCAAB teams  
        ncaab_teams = ['uconn', "st. john's", 'duke', 'north carolina', 'kansas',
                       'purdue', 'oregon', 'utah']
        
        # NFL teams
        nfl_teams = ['chiefs', 'bills', 'ravens', 'bengals', 'steelers', 'browns',
                     'texans', 'colts', 'titans', 'jaguars', 'saints', 'falcons',
                     'panthers', 'buccaneers', 'eagles', 'cowboys', 'giants', 'commanders',
                     'rams', '49ers', 'seahawks', 'cardinals', 'broncos', 'chargers',
                     'raiders', 'chiefs', 'packers', 'vikings', 'lions', 'bears',
                     'patriots', 'dolphins', 'jets']
        
        # NHL teams
        nhl_teams = ['bruins', 'maple leafs', 'rangers', 'devils', 'flyers',
                     'avalanche', 'wild', 'golden knights', 'kings', 'sharks',
                     'ducks', 'canucks', 'capitals', 'hurricanes', 'blue jackets',
                     'islanders', 'penguins', 'stars', 'blackhawks', 'red wings',
                     'lightning', 'panthers', 'kraken', 'flames', 'oilers', 'jets']
        
        # Soccer teams
        soccer_teams = ['leeds', 'nottingham forest', 'manchester', 'liverpool', 'arsenal',
                        'chelsea', 'tottenham', 'everton', 'west ham', 'newcastle',
                        'fulham', 'crystal palace', 'brighton', 'sunderland', 'aston villa']
        
        # Player names (helps detect sport)
        nba_players = ['anthony edwards', 'derrick white', 'de\'aaron fox', 'paolo banchero',
                       'lamelo ball']
        ncaab_players = ['stephon castle']
        
        # Check context clues - order matters, check most specific first
        if any(team in search_text for team in nba_teams) or any(p in search_text for p in nba_players):
            return await self.sports.get_by_league_code("nba")
        elif any(team in search_text for team in nfl_teams):
            return await self.sports.get_by_league_code("nfl")
        elif any(team in search_text for team in nhl_teams):
            return await self.sports.get_by_league_code("nhl")
        elif any(team in search_text for team in ncaab_teams) or any(p in search_text for p in ncaab_players):
            return await self.sports.get_by_league_code("ncaab")
        elif any(team in search_text for team in soccer_teams):
            # For soccer, we need to search by name since league_code is "eng.1" not "soccer"
            stmt = select(Sport).where(Sport.name == 'soccer')
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        
        return None

    async def _find_game(self, game_str: str, date_str: str = None, sport_id: int = None) -> Optional[Any]:
        """Find a game by team names and date - query database first, then ESPN API"""
        teams = [t.strip() for t in game_str.split('vs')]
        if len(teams) != 2:
            return None
        
        team1, team2 = teams[0].lower(), teams[1].lower()
        
        # First, try to find in local database
        games = await self.games.list()
        
        for game in games:
            home = (game.home_team_name or '').lower()
            away = (game.away_team_name or '').lower()
            
            # Check if teams match (both orderings)
            home_match = team1 in home or home in team1
            away_match = team2 in away or away in team2
            
            reverse_home_match = team2 in home or home in team2
            reverse_away_match = team1 in away or away in team1
            
            teams_match = (home_match and away_match) or (reverse_home_match and reverse_away_match)
            
            if teams_match:
                # Check date if provided
                if date_str:
                    if game.start_time:
                        game_date = game.start_time.date()
                        try:
                            import datetime as dt
                            search_date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
                            if game_date != search_date:
                                continue
                        except:
                            pass
                
                return game
        
        # If not found in database, query ESPN API
        if sport_id:
            sport = await self.sports.get(sport_id)
            if sport:
                game_from_espn = await self._find_game_in_espn(team1, team2, date_str, sport.name)
                if game_from_espn:
                    return game_from_espn
        
        return None

    async def _find_game_in_espn(self, team1: str, team2: str, date_str: str = None, sport_name: str = None) -> Optional[Dict]:
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
                
                home_team = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_team = next((c for c in competitors if c.get("homeAway") == "away"), None)
                
                if not home_team or not away_team:
                    continue
                
                home_name = (home_team.get("team", {}).get("displayName") or "").lower()
                away_name = (away_team.get("team", {}).get("displayName") or "").lower()
                
                # Check team matches
                team1_match = (team1 in home_name or home_name in team1 or 
                             team1 in away_name or away_name in team1)
                team2_match = (team2 in home_name or home_name in team2 or 
                             team2 in away_name or away_name in team2)
                
                if not (team1_match and team2_match):
                    continue
                
                # Check date if provided
                if date_str:
                    try:
                        import datetime as dt
                        game_date_str = event.get("date", "")
                        # Parse ESPN date format (2026-02-07T20:00Z)
                        game_date = dt.datetime.fromisoformat(game_date_str.replace('Z', '+00:00')).date()
                        search_date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
                        if game_date != search_date:
                            continue
                    except:
                        pass
                
                # Return a dict-like object with the game info
                return type('Game', (), {
                    'game_id': event.get('id'),
                    'home_team_name': home_team.get("team", {}).get("displayName"),
                    'away_team_name': away_team.get("team", {}).get("displayName"),
                    'start_time': event.get("date"),
                })()
        
        except Exception as e:
            print(f"Error querying ESPN API: {e}")
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
        elif "ufc" in t:
            sport = await self.sports.get_by_league_code("ufc")

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