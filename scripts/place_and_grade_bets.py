#!/usr/bin/env python3
"""Place bets, link to ESPN, grade, and cleanup voided parlays"""
import asyncio
import re
import sqlite3
import sys
import uuid
from datetime import datetime, UTC
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.espn_client import ESPNClient

BET_TEXT = """Type: 3 Leg Parlay
Celtics ML | Feb 6 | -150 | $100 | Matchup edge.
Bucks ML | Feb 6 | -140 | $100 | Efficiency advantage.
Anthony Edwards over 27.5 pts | Feb 6 | -110 | $100 | High usage.

Type: 2 Leg Parlay
Kings ML | Feb 6 | -200 | $125 | Home court.
De'Aaron Fox over 25.5 pts | Feb 6 | -110 | $125 | Volume scorer.

Type: 2 Leg Parlay
UConn ML | Feb 6 | -160 | $125 | Depth advantage.
Stephon Castle over 15.5 pts | Feb 6 | -110 | $125 | Scoring role.

Derrick White over 5.5 assists | Feb 6 | -110 | $100 | Playmaking."""

SPORT_PATHS = {
    "nba": ("basketball", "nba"),
    "ncaab": ("basketball", "mens-college-basketball"),
}

def parse_pipe_format(text: str) -> List[Dict]:
    """Parse pipe-separated bet format"""
    bets = []
    lines = text.strip().split('\n')
    current_parlay_id = None
    leg_count = 0
    original_stake = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            current_parlay_id = None
            continue
        
        if line.lower().startswith('type:'):
            # Extract parlay info
            match = re.search(r'(\d+)\s+leg', line.lower())
            leg_count = int(match.group(1)) if match else 1
            current_parlay_id = str(uuid.uuid4())
            original_stake = 0
            continue
        
        # Parse bet line: Selection | Date | Odds | Stake | Reason
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4:
            continue
        
        selection = parts[0]
        date_str = parts[1]
        odds = float(parts[2])
        stake_str = parts[3].replace('$', '').replace(',', '')
        stake = float(stake_str)
        reason = parts[4] if len(parts) > 4 else ""
        
        # Calculate original stake for parlay
        if current_parlay_id and leg_count > 1:
            original_stake = stake * leg_count
        else:
            original_stake = stake
        
        # Detect bet type
        if ' ML' in selection or ' ml' in selection:
            bet_type = 'moneyline'
            player_name = None
        elif ' over ' in selection.lower() or ' under ' in selection.lower():
            bet_type = 'prop'
            player_name = selection.split(' over')[0].split(' under')[0].strip().lower()
        else:
            bet_type = 'moneyline'
            player_name = None
        
        # Detect sport
        if 'UConn' in selection or 'Castle' in selection:
            sport = 'ncaab'
        else:
            sport = 'nba'
        
        bets.append({
            'selection': selection,
            'bet_type': bet_type,
            'player_name': player_name,
            'stake': stake,
            'original_stake': original_stake,
            'odds': odds,
            'reason': reason,
            'parlay_id': current_parlay_id,
            'date': date_str,
            'sport': sport
        })
    
    return bets


async def main():
    print("Parsing bets...")
    bets = parse_pipe_format(BET_TEXT)
    print(f"Parsed {len(bets)} bets")
    
    # Insert into database
    db = sqlite3.connect("sports_intel.db")
    cursor = db.cursor()
    
    # Get sport IDs
    cursor.execute("SELECT id, espn_league_code FROM sports WHERE espn_league_code IN ('nba', 'ncaab')")
    sport_map = {row[1]: row[0] for row in cursor.fetchall()}
    
    placed_at = datetime.now(UTC).isoformat()
    
    for bet in bets:
        sport_id = sport_map.get(bet['sport'])
        if not sport_id:
            print(f"Warning: Unknown sport {bet['sport']}")
            continue
        
        cursor.execute("""
            INSERT INTO bets (
                placed_at, sport_id, bet_type, selection, player_name, stake, original_stake,
                odds, status, parlay_id, reason, raw_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            placed_at, sport_id, bet['bet_type'], bet['selection'], bet['player_name'],
            bet['stake'], bet['original_stake'], bet['odds'], bet['parlay_id'], bet['reason'], bet['selection']
        ))
    
    db.commit()
    print(f"Inserted {len(bets)} bets into database")
    
    # Now link to ESPN and grade
    sys.path.insert(0, str(Path(__file__).parent))
    from backfill_bets_from_text import find_event_id, fetch_moneyline_odds
    from upsert_games_from_espn import upsert_game_from_event
    from grade_props_from_espn import get_player_stat
    
    client = ESPNClient()
    
    # Link bets to games
    print("\nLinking bets to ESPN games...")
    cursor.execute("SELECT id, selection, bet_type FROM bets WHERE game_id IS NULL")
    pending_bets = cursor.fetchall()
    
    for bet_id, selection, bet_type in pending_bets:
        # Determine sport and game text
        if 'UConn' in selection or 'Castle' in selection:
            sport = 'ncaab'
            if bet_type == 'prop':
                game_text = "UConn vs St. John's"
            else:
                game_text = selection.replace(' ML', '')
        else:
            sport = 'nba'
            if bet_type == 'prop':
                player_part = selection.split(' over')[0].split(' under')[0]
                if 'Edwards' in player_part:
                    game_text = "Minnesota Timberwolves vs New Orleans Pelicans"
                elif 'Fox' in player_part:
                    game_text = "Sacramento Kings vs LA Clippers"
                elif 'White' in player_part:
                    game_text = "Boston Celtics vs Miami Heat"
            else:
                team = selection.replace(' ML', '').strip()
                if 'Celtics' in team:
                    game_text = "Boston Celtics vs Miami Heat"
                elif 'Bucks' in team:
                    game_text = "Milwaukee Bucks vs Indiana Pacers"
                elif 'Kings' in team:
                    game_text = "Sacramento Kings vs LA Clippers"
        
        event_id = await find_event_id(client, sport, game_text, "2026-02-06")
        if event_id:
            cursor.execute("UPDATE bets SET game_id = ? WHERE id = ?", (event_id, bet_id))
            print(f"  Linked bet #{bet_id} to event {event_id}")
    
    db.commit()
    
    # Upsert games from ESPN
    print("\nFetching game data from ESPN...")
    cursor.execute("SELECT DISTINCT game_id FROM bets WHERE game_id IS NOT NULL")
    game_ids = [row[0] for row in cursor.fetchall()]
    
    for game_id in game_ids:
        await upsert_game_from_event(client, game_id, cursor, db)
        print(f"  Updated game {game_id}")
    
    # Grade bets
    print("\nGrading bets...")
    cursor.execute("SELECT id, bet_type, selection, player_name, stake, odds, game_id, parlay_id FROM bets WHERE status = 'pending'")
    pending = cursor.fetchall()
    
    for bet_id, bet_type, selection, player_name, stake, odds, game_id, parlay_id in pending:
        if bet_type == 'moneyline':
            # Grade moneyline
            cursor.execute("SELECT home_team_name, away_team_name, home_score, away_score, status FROM games WHERE game_id = ?", (game_id,))
            game = cursor.fetchone()
            if not game or game[4] != 'final':
                continue
            
            home_team, away_team, home_score, away_score, status = game
            team_name = selection.replace(' ML', '').strip().lower()
            
            if team_name in home_team.lower():
                won = home_score > away_score
            elif team_name in away_team.lower():
                won = away_score > home_score
            else:
                continue
            
            if won:
                profit = stake * (odds / 100) if odds > 0 else stake / (abs(odds) / 100)
                cursor.execute("UPDATE bets SET status = 'won', profit = ?, graded_at = ? WHERE id = ?",
                             (profit, datetime.now(UTC).isoformat(), bet_id))
            else:
                cursor.execute("UPDATE bets SET status = 'lost', profit = ?, graded_at = ? WHERE id = ?",
                             (-stake, datetime.now(UTC).isoformat(), bet_id))
            print(f"  Graded bet #{bet_id}: {'WON' if won else 'LOST'}")
        
        elif bet_type == 'prop' and player_name:
            # Grade prop
            stat_key = 'points' if 'pts' in selection else 'assists'
            
            # Get sport for this bet
            cursor.execute("SELECT s.espn_league_code FROM bets b JOIN sports s ON b.sport_id = s.id WHERE b.id = ?", (bet_id,))
            sport_row = cursor.fetchone()
            sport = sport_row[0] if sport_row else 'nba'
            
            result = await get_player_stat(client, sport, sport, game_id, player_name, stat_key)
            
            if result is None:
                cursor.execute("UPDATE bets SET status = 'void', profit = 0, graded_at = ? WHERE id = ?",
                             (datetime.now(UTC).isoformat(), bet_id))
                print(f"  Voided bet #{bet_id}: {player_name} (no stats found)")
                continue
            
            athlete_name, stat_value_str = result
            stat_value = float(stat_value_str)
            
            line_match = re.search(r'(over|under)\s+([\d.]+)', selection.lower())
            if not line_match:
                continue
            
            direction = line_match.group(1)
            line = float(line_match.group(2))
            
            if direction == 'over':
                won = stat_value > line
            else:
                won = stat_value < line
            
            if won:
                profit = stake * (odds / 100) if odds > 0 else stake / (abs(odds) / 100)
                cursor.execute("UPDATE bets SET status = 'won', profit = ?, result_value = ?, graded_at = ? WHERE id = ?",
                             (profit, stat_value, datetime.now(UTC).isoformat(), bet_id))
            else:
                cursor.execute("UPDATE bets SET status = 'lost', profit = ?, result_value = ?, graded_at = ? WHERE id = ?",
                             (-stake, stat_value, datetime.now(UTC).isoformat(), bet_id))
            print(f"  Graded bet #{bet_id}: {'WON' if won else 'LOST'} ({athlete_name}: {stat_value} vs {line})")
    
    db.commit()
    
    # Calculate parlay odds
    print("\nCalculating parlay odds...")
    cursor.execute("SELECT DISTINCT parlay_id FROM bets WHERE parlay_id IS NOT NULL")
    parlay_ids = [row[0] for row in cursor.fetchall()]
    
    for parlay_id in parlay_ids:
        cursor.execute("SELECT odds FROM bets WHERE parlay_id = ?", (parlay_id,))
        leg_odds = [row[0] for row in cursor.fetchall()]
        
        # Calculate combined parlay odds
        decimal_odds = []
        for odds in leg_odds:
            if odds > 0:
                decimal_odds.append((odds / 100) + 1)
            else:
                decimal_odds.append((100 / abs(odds)) + 1)
        
        combined_decimal = 1.0
        for d in decimal_odds:
            combined_decimal *= d
        
        if combined_decimal >= 2.0:
            parlay_odds = (combined_decimal - 1) * 100
        else:
            parlay_odds = -100 / (combined_decimal - 1)
        
        cursor.execute("UPDATE bets SET parlay_odds = ? WHERE parlay_id = ?", (parlay_odds, parlay_id))
        print(f"  Parlay {parlay_id[:8]}: {parlay_odds:+.0f}")
    
    db.commit()
    
    # Delete parlays with voided legs
    print("\nCleaning up parlays with voided legs...")
    cursor.execute("""
        SELECT DISTINCT parlay_id FROM bets 
        WHERE parlay_id IS NOT NULL 
        AND status = 'void'
    """)
    voided_parlays = [row[0] for row in cursor.fetchall()]
    
    for parlay_id in voided_parlays:
        cursor.execute("DELETE FROM bets WHERE parlay_id = ?", (parlay_id,))
        print(f"  Deleted parlay {parlay_id[:8]} (had voided leg)")
    
    db.commit()
    db.close()
    
    print("\n✅ Done! All bets placed, graded, and voided parlays removed.")


if __name__ == "__main__":
    asyncio.run(main())
