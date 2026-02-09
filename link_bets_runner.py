#!/usr/bin/env python3
import asyncio
import sqlite3
import re
from difflib import SequenceMatcher
import sys

sys.path.insert(0, '/Users/dakotanicol/sports_betting_dashboard')

from backend.services.espn_client import ESPNClient

def similarity(a, b):
    """Calculate string similarity ratio"""
    return SequenceMatcher(None, a, b).ratio()

async def find_game_by_teams(sport: str, team1: str, team2: str, date: str):
    """Find game by team names and date"""
    client = ESPNClient()
    
    # Get games for the sport
    games = await client.get_games(sport, date)
    
    if not games:
        return None
    
    # Normalize team names
    team1_lower = team1.lower().strip()
    team2_lower = team2.lower().strip()
    
    for game in games:
        home = game.get('home_team', '').lower().strip()
        away = game.get('away_team', '').lower().strip()
        
        # Check if teams match (either ordering)
        match1 = (similarity(team1_lower, home) > 0.7 and similarity(team2_lower, away) > 0.7)
        match2 = (similarity(team1_lower, away) > 0.7 and similarity(team2_lower, home) > 0.7)
        
        if match1 or match2:
            return game
    
    return None

def detect_sport(game_info: str) -> str:
    """Detect sport from game info text"""
    game_lower = game_info.lower()
    
    if any(team in game_lower for team in ['celtics', 'heat', 'bucks', 'pacers', 'timberwolves', 'pelicans', 'kings', 'clippers']):
        return 'nba'
    elif any(team in game_lower for team in ['uconn', "st. john's"]):
        return 'college-basketball'
    elif any(team in game_lower for team in ['leeds', 'nottingham', 'arsenal', 'man city', 'liverpool']):
        return 'soccer'
    elif any(team in game_lower for team in ['chiefs', 'patriots', 'cowboys', 'packers']):
        return 'nfl'
    
    return 'nba'

def parse_bets_from_text(text: str) -> list:
    """Parse bets from raw text format"""
    bets = []
    
    # Split by Type: to find individual bets
    bet_blocks = re.split(r'(?=Type:)', text.strip())
    
    for block in bet_blocks:
        if not block.strip():
            continue
        
        bet = {}
        
        # Extract fields
        type_match = re.search(r'Type:\s*(\w+)', block)
        selection_match = re.search(r'Selection:\s*([^,]+)', block)
        game_match = re.search(r'Game:\s*([^,]+)', block)
        date_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2})', block)
        odds_match = re.search(r'Odds:\s*([-+]?\d+)', block)
        stake_match = re.search(r'Stake:\s*(\d+)', block)
        reason_match = re.search(r'Reason:\s*([^.]+)', block)
        
        if all([type_match, selection_match, game_match, date_match, stake_match]):
            bet['type'] = type_match.group(1).lower()
            bet['selection'] = selection_match.group(1).strip()
            bet['game'] = game_match.group(1).strip()
            bet['date'] = date_match.group(1)
            bet['odds'] = int(odds_match.group(1)) if odds_match else -110
            bet['stake'] = int(stake_match.group(1))
            bet['reason'] = reason_match.group(1).strip() if reason_match else ''
            bet['sport'] = detect_sport(bet['game'])
            
            bets.append(bet)
    
    return bets

async def link_bets_to_games(bet_text: str) -> None:
    """Link bets from raw text to games and update database"""
    # Parse bets
    bets = parse_bets_from_text(bet_text)
    print(f"📋 Parsed {len(bets)} bets from text\n")
    
    # Group bets by game
    games_to_find = {}
    for bet in bets:
        game_key = (bet['sport'], bet['game'], bet['date'])
        if game_key not in games_to_find:
            games_to_find[game_key] = []
        games_to_find[game_key].append(bet)
    
    conn = sqlite3.connect('/Users/dakotanicol/sports_betting_dashboard/sports_intel.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find each game
    for (sport, game_info, date), sport_bets in games_to_find.items():
        print(f"🔍 Searching for: {sport.upper()}: {game_info} ({date})")
        
        # Parse team names from game info
        teams = game_info.split(' vs ')
        if len(teams) != 2:
            print(f"  ❌ Could not parse teams from '{game_info}'")
            continue
        
        team1, team2 = teams[0].strip(), teams[1].strip()
        
        # Find the game
        game = await find_game_by_teams(sport, team1, team2, date)
        
        if not game:
            print(f"  ❌ Game not found in ESPN database")
            continue
        
        game_id = game.get('id')
        
        print(f"  ✅ Found: {game['away_team']} @ {game['home_team']}")
        print(f"     Game ID: {game_id}")
        
        # Update bets with game_id
        updated_count = 0
        for bet in sport_bets:
            cursor.execute("""
                UPDATE bets 
                SET game_id = ?
                WHERE game_id IS NULL 
                AND DATE(placed_at) = ?
                AND LOWER(selection) LIKE LOWER(?)
            """, (game_id, date, f"%{bet['selection'][:20]}%"))
            
            if cursor.rowcount > 0:
                updated_count += cursor.rowcount
                print(f"    ✅ Updated bet: {bet['selection']}")
        
        if updated_count > 0:
            conn.commit()
            print(f"  ✅ Linked {updated_count} bets to this game")
        
        print()
    
    conn.close()
    print("✅ All done! Bets are now linked to games.")

if __name__ == "__main__":
    bet_text = """Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -150, Stake: 300, Reason: Matchup edge.
Type: moneyline, Selection: Bucks ML, Game: Bucks vs Pacers, Date: 2026-02-06, Odds: -140, Stake: 300, Reason: Efficiency advantage.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-06, Odds: -110, Stake: 300, Reason: High usage.
Type: moneyline, Selection: Kings ML, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -130, Stake: 250, Reason: Home edge.
Type: prop, Selection: De'Aaron Fox over 25.5 pts, Game: Kings vs Clippers, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Favorable matchup.
Type: moneyline, Selection: UConn ML, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -180, Stake: 250, Reason: Power rating advantage.
Type: prop, Selection: Stephon Castle over 15.5 pts, Game: St. John's vs UConn, Date: 2026-02-06, Odds: -110, Stake: 250, Reason: Usage projection.
Type: moneyline, Selection: Leeds ML, Game: Leeds vs Nottingham Forest, Date: 2026-02-06, Odds: -120, Stake: 100, Reason: Home form advantage.
Type: prop, Selection: Derrick White over 5.5 assists, Game: Celtics vs Heat, Date: 2026-02-06, Odds: -110, Stake: 100, Reason: Increased playmaking role."""
    
    asyncio.run(link_bets_to_games(bet_text))
