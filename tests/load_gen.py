import asyncio
import aiohttp
import sys
import time

ACTION_DELAY = 10
AGENT_COUNTS = [10, 25, 50, 100]
API_URL = "http://127.0.0.1:8012/api/v1/sim/control" # Dedicated port 8012 for Load Test

async def ramp_load():
    async with aiohttp.ClientSession() as session:
        print(f"Waiting for server at {API_URL}...")
        
        # Wait for server
        for _ in range(30):
            try:
                async with session.get("http://127.0.0.1:8012/docs") as resp:
                    if resp.status == 200:
                        break
            except:
                await asyncio.sleep(1)
        else:
            print("Server not found!")
            return

        print("Server found. Starting Ramp Up...")
        
        for count in AGENT_COUNTS:
            print(f"Setting Agent Count to {count}...")
            async with session.post(API_URL, json={
                "action": "start", 
                "config": {"num_agents": count, "grid_size": 20} # Larger grid for more agents
            }) as resp:
                print(f"Response: {resp.status}")
                
            print(f"Holding for {ACTION_DELAY}s...")
            await asyncio.sleep(ACTION_DELAY)
            
        print("Load Ramp Finished.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(ramp_load())
