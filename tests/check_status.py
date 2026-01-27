import asyncio
import aiohttp
import sys

API_URL = "http://127.0.0.1:8012/api/v1/sim/state"

async def check():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data)
                    print(f"Current Agent Count: {count}")
                else:
                    print(f"Error: {resp.status}")
        except Exception as e:
            print(f"Connection Failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())
