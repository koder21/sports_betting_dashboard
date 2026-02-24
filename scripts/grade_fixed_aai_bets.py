#!/usr/bin/env python3
"""Manually grade the fixed AAI bets."""

import asyncio
from backend.db import init_db, get_session
from backend.services.betting.grader import BetGrader
from backend.repositories.bet_repo import BetRepository

async def main():
    await init_db()
    
    async for session in get_session():
        bet_repo = BetRepository(session)
        grader = BetGrader(session)
        
        # Get the AAI bets that we just fixed
        pending_bets = await bet_repo.list_pending()
        aai_bets = [b for b in pending_bets if "AAI" in (b.reason or "")]
        
        print(f"Found {len(aai_bets)} AAI bets to grade:\n")
        
        for bet in aai_bets:
            print(f"Grading Bet {bet.id}: {bet.selection}")
            result = await grader.grade(bet)
            
            if result:
                print(f"  ✓ Graded as: {result.get('status', 'unknown')}")
                if 'profit' in result:
                    print(f"  Profit/Loss: ${result['profit']:.2f}")
            else:
                print(f"  ⚠ Not graded (game not final?)")
            print()
        
        await session.commit()
        await grader.close()

if __name__ == "__main__":
    asyncio.run(main())
