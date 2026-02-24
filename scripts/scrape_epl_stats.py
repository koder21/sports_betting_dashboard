#!/usr/bin/env python3
"""Script to scrape EPL player stats for completed games"""
import asyncio
import sqlite3
from backend.services.espn_client import ESPNClient
from backend.services.scraper_stats import PlayerStatsScraper
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def main():
    # Get all EPL games with FT status
    conn = sqlite3.connect("sports_intel.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT game_id FROM games 
        WHERE sport='EPL' 
        AND (status='FT' OR status='FINAL' OR status LIKE '%final%' OR status LIKE '%Full Time%')
    """)
    epl_games = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(epl_games)} completed EPL games: {epl_games}")
    
    engine = create_async_engine("sqlite+aiosqlite:///sports_intel.db", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        client = ESPNClient()
        scraper = PlayerStatsScraper(client, session)
        
        total_stats = 0
        for game_id in epl_games:
            try:
                print(f"Scraping EPL game {game_id}...", end=" ")
                stats = await scraper._scrape_game_boxscore(str(game_id), "soccer", "eng.1", "EPL")
                print(f"✓ {stats} player stats")
                total_stats += stats
            except Exception as e:
                print(f"✗ ERROR - {e}")
        
        await session.commit()
        print(f"\n✓ Total EPL stats added to database: {total_stats}")
        
    # Verify stats are in database
    conn = sqlite3.connect("sports_intel.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_stats WHERE game_id IN (SELECT game_id FROM games WHERE sport='EPL')")
    final_count = cursor.fetchone()[0]
    conn.close()
    print(f"✓ Verified EPL stats in database: {final_count}")


if __name__ == "__main__":
    asyncio.run(main())
