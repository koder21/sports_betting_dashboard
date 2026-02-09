import asyncio
import aiohttp
from datetime import datetime

async def test_ncaab():
    # Try CDN endpoint
    url = "https://cdn.espn.com/core/mens-college-basketball/scoreboard?xhr=1"
    
    print(f"Trying CDN endpoint: {url}")
    session = aiohttp.ClientSession()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response length: {len(text)}")
            if "UConn" in text or "Connecticut" in text:
                print("✓ Found UConn in response!")
                # Find and print the relevant section
                idx = text.find("UConn")
                print(text[max(0, idx-200):idx+200])
            elif "St. John" in text or "St John" in text:
                print("✓ Found St. John's in response!")
                idx = text.find("St. John")
                print(text[max(0, idx-200):idx+200])
            else:
                print("✗ UConn/St. John's not found in response")
                print(f"First 500 chars: {text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await session.close()

asyncio.run(test_ncaab())
