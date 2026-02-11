from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from collections import defaultdict

from ...repositories.bet_repo import BetRepository


class PlayerTrendAnalytics:
    """Track hot/cold player indicators"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bets = BetRepository(session)

    async def hot_cold_players(self, games_window: int = 5) -> Dict[str, Any]:
        """
        Analyze hot/cold players based on actual game performance
        Uses all games scraped, not just games bet on
        Compares last N games performance to season average
        """
        # Query player_stats directly from the database
        from ...models.player_stats import PlayerStats
        from ...models.player import Player
        
        result = await self.session.execute(
            text("""
                SELECT ps.player_id, p.name, ps.sport, ps.points, ps.game_id, g.start_time
                FROM player_stats ps
                LEFT JOIN players p ON ps.player_id = p.player_id
                LEFT JOIN games_results g ON ps.game_id = g.game_id
                WHERE ps.points IS NOT NULL
                ORDER BY ps.player_id, g.start_time DESC
            """)
        )
        
        rows = result.fetchall()
        
        if not rows:
            return {"hot_players": [], "cold_players": [], "trending": []}
        
        # Group player stats by player_id
        player_stats = defaultdict(list)
        player_info = {}
        
        for row in rows:
            player_id, name, sport, points, game_id, start_time = row
            # Skip players without names (orphaned records)
            if not name:
                continue
            player_stats[player_id].append({
                "points": points,
                "date": start_time,
                "game_id": game_id
            })
            if player_id not in player_info:
                player_info[player_id] = {
                    "name": name,
                    "sport": sport or "Unknown",
                    "team": "N/A"
                }
        
        if not player_stats:
            return {"hot_players": [], "cold_players": [], "trending": []}
        
        # Sort by date for each player
        for player_id in player_stats:
            player_stats[player_id].sort(key=lambda x: x["date"] or "", reverse=True)
        
        hot_players = []
        cold_players = []
        trending = []
        
        for player_id, stats in player_stats.items():
            if len(stats) < 1:
                continue
            
            # Calculate recent average points
            recent = stats[:games_window]
            recent_avg = sum(s["points"] for s in recent) / len(recent) if recent else 0
            
            # Calculate season average points
            season_avg = sum(s["points"] for s in stats) / len(stats) if stats else 0
            
            # Determine trend - difference from season average
            diff = recent_avg - season_avg
            
            info = player_info.get(player_id, {})
            player_record = {
                "player_id": player_id,
                "name": info.get("name"),
                "sport": info.get("sport"),
                "team": info.get("team"),
                "season_avg_pts": round(season_avg, 1),
                "recent_avg_pts": round(recent_avg, 1),
                "trend": round(diff, 1),
                "recent_games": len(recent),
                "total_games": len(stats)
            }
            
            # Classify as hot/cold based on standard deviation
            # Hot: significantly above season average, Cold: significantly below
            if len(stats) > 1:
                # Calculate standard deviation
                variance = sum((s["points"] - season_avg) ** 2 for s in stats) / len(stats)
                std_dev = variance ** 0.5
                
                if diff > std_dev and diff > 1:  # Hot: above avg + meaningful gap
                    hot_players.append(player_record)
                elif diff < -std_dev and diff < -1:  # Cold: below avg + meaningful gap
                    cold_players.append(player_record)
            else:
                # Single game - classify by performance vs season average
                if recent_avg > season_avg + 2:  # Had a great game
                    hot_players.append(player_record)
                elif recent_avg < season_avg - 2:  # Had a poor game
                    cold_players.append(player_record)
            
            if diff != 0:
                trending.append(player_record)
        
        # Sort by trend magnitude
        hot_players.sort(key=lambda x: x["trend"], reverse=True)
        cold_players.sort(key=lambda x: x["trend"])
        trending.sort(key=lambda x: abs(x["trend"]), reverse=True)
        
        return {
            "hot_players": hot_players[:10],
            "cold_players": cold_players[:10],
            "trending": trending[:15]
        }


class TeamTrendAnalytics:
    """Track team momentum and home/away splits"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def team_momentum(self, games_window: int = 5) -> Dict[str, Any]:
        """Calculate team momentum (last N games record)"""
        # Query games_results to get team performance
        query = text("""
            SELECT 
                CASE WHEN home_team_id = :team_id THEN home_team_id ELSE away_team_id END as team_id,
                CASE WHEN home_team_id = :team_id THEN home_team ELSE away_team END as team_name,
                sport,
                CASE 
                    WHEN home_team_id = :team_id AND home_score > away_score THEN 'W'
                    WHEN away_team_id = :team_id AND away_score > home_score THEN 'W'
                    ELSE 'L'
                END as result,
                start_time
            FROM games_results
            WHERE home_team_id = :team_id OR away_team_id = :team_id
            ORDER BY start_time DESC
            LIMIT :limit
        """)
        
        # Get all unique teams
        teams_query = text("SELECT DISTINCT home_team_id, home_team FROM games_results")
        teams_result = await self.session.execute(teams_query)
        teams = [{"id": row[0], "name": row[1]} for row in teams_result.fetchall()]
        
        momentum_data = []
        
        for team in teams:
            result = await self.session.execute(
                query,
                {"team_id": team["id"], "limit": games_window}
            )
            games = [row for row in result.fetchall()]
            
            if not games:
                continue
            
            wins = sum(1 for game in games if game[3] == 'W')
            losses = len(games) - wins
            record = f"{wins}-{losses}"
            win_rate = (wins / len(games)) * 100 if games else 0
            
            # Determine momentum status: FIRE (4+ wins in last 5) or FREEZING (4+ losses in last 5)
            momentum_status = None
            if wins >= 4:
                momentum_status = "FIRE"
            elif losses >= 4:
                momentum_status = "FREEZING"
            
            momentum_data.append({
                "team_id": team["id"],
                "team_name": team["name"],
                "sport": games[0][2] if games else "Unknown",
                "record": record,
                "win_rate": round(win_rate, 1),
                "games": games_window,
                "momentum_status": momentum_status
            })
        
        momentum_data.sort(key=lambda x: x["win_rate"], reverse=True)
        return {"momentum": momentum_data}

    async def home_away_splits(self) -> Dict[str, Any]:
        """Calculate home vs away performance for teams"""
        query = text("""
            SELECT 
                home_team_id,
                home_team,
                sport,
                COUNT(*) as games,
                SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(home_score), 1) as avg_points_for,
                ROUND(AVG(away_score), 1) as avg_points_against
            FROM games_results
            GROUP BY home_team_id, home_team, sport
            
            UNION ALL
            
            SELECT 
                away_team_id,
                away_team,
                sport,
                COUNT(*) as games,
                SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(away_score), 1) as avg_points_for,
                ROUND(AVG(home_score), 1) as avg_points_against
            FROM games_results
            GROUP BY away_team_id, away_team, sport
        """)
        
        result = await self.session.execute(query)
        splits_data = []
        
        for row in result.fetchall():
            team_id, team_name, sport, games, wins, losses, ppf, ppa = row
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            
            splits_data.append({
                "team_id": team_id,
                "team_name": team_name,
                "sport": sport,
                "games": games,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "avg_points_for": ppf,
                "avg_points_against": ppa
            })
        
        return {"splits": splits_data}
