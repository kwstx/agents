import asyncio
import aiohttp
import time
import random
import logging
import sys
import subprocess
import os

# Configuration
PORT = 8008 # Use different port than restart test to avoid conflict if both run
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RACE_TEST")

def start_server_process():
    cmd = [sys.executable, "-m", "uvicorn", "agent_forge.server.api:app", 
           "--host", HOST, "--port", str(PORT)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + ";" + os.path.join(os.getcwd(), "src")
    # Redirect to a file for debugging
    with open("race_server.log", "w") as f:
        proc = subprocess.Popen(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)
    return proc

async def wait_for_server():
    async with aiohttp.ClientSession() as session:
        for _ in range(60):
            try:
                async with session.get(f"{API_URL}/docs") as resp:
                    if resp.status == 200:
                        return True
            except:
                await asyncio.sleep(0.5)
    return False

async def worker(worker_id: int, session: aiohttp.ClientSession):
    """
    Spams control commands.
    """
    actions = ["start", "pause", "resume", "stop"]
    
    for _ in range(10): # 10 requests per worker
        action = random.choice(actions)
        payload = {"action": action}
        
        if action == "start":
            # Randomize start config slightly
            payload["config"] = {
                "num_agents": random.randint(2, 5),
                "grid_size": 10
            }
            
        try:
            async with session.post(f"{API_URL}/api/v1/sim/control", json=payload) as resp:
                data = await resp.json()
                # We expect 200 OK mostly, maybe some errors if logic forbids (e.g. resume when not started)
                # But we definitely want NO internal server errors (500)
                if resp.status >= 500:
                    logger.error(f"Worker {worker_id} got 500 ERROR on {action}: {data}")
                    return False
        except Exception as e:
            logger.error(f"Worker {worker_id} exception: {e}")
            return False
            
        await asyncio.sleep(random.random() * 0.1) # Small jitter
        
    return True

async def main():
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            return
            
        logger.info("Server Up. Starting Race...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Spawn 20 workers
            tasks = [worker(i, session) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            if all(results):
                logger.info(">>> ALL WORKERS FINISHED SUCCESSFULLY (No Crashes/500s).")
            else:
                logger.error(">>> SOME WORKERS FAILED.")
                sys.exit(1)
                
            # 2. Final Sanity Check
            async with session.get(f"{API_URL}/api/sim/status") as resp:
                status = await resp.json()
                logger.info(f"Final Status: {status}")
                # Should be valid JSON, no corruption
                assert "status" in status
                
    finally:
        logger.info("Killing Server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
