import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json
import time

# Configuration
PORT = 8018
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("DEMO")

def start_server_process():
    cmd = [sys.executable, "-m", "uvicorn", "agent_forge.server.api:app", 
           "--host", HOST, "--port", str(PORT)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + ";" + os.path.join(os.getcwd(), "src")
    with open("demo_server.log", "w") as f:
        proc = subprocess.Popen(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)
    return proc

async def wait_for_server():
    async with aiohttp.ClientSession() as session:
        for _ in range(20):
            try:
                async with session.get(f"{API_URL}/docs") as resp:
                    if resp.status == 200:
                        return True
            except:
                await asyncio.sleep(0.5)
    return False

async def run_scenario():
    logger.info("🎬 STARTING EXECUTIVE DEMO SCENARIO")
    logger.info("-----------------------------------")
    
    proc = start_server_process()
    try:
        if not await wait_for_server():
            logger.error("Failed to start server.")
            return

        async with aiohttp.ClientSession() as session:
            # 1. Start Phase: NORMAL OPERATIONS
            logger.info("ACT 1: NORMAL OPERATIONS (Green State)")
            logger.info("Starting fleet with optimized density...")
            await session.post(f"{API_URL}/api/v1/sim/control", 
                               json={"action": "start", "config": {"num_agents": 6, "grid_size": 10}}) 
            
            logger.info(">> System running smoothly. Agents performing tasks.")
            await asyncio.sleep(5)
            
            # 2. Start Phase: DEGRADATION (Increased Load)
            logger.info("\nACT 2: SYSTEM DEGRADATION (Yellow State)")
            logger.info("Injecting load spike (Restarting with High Density)...") 
            # We restart with more agents to force congestion
            await session.post(f"{API_URL}/api/v1/sim/control", 
                               json={"action": "start", "config": {"num_agents": 12, "grid_size": 8}})
            
            logger.info(">> Congestion increasing. Risk score should be rising.")
            await asyncio.sleep(5)
            
            # 3. Start Phase: FAILURE (Red State)
            logger.info("\nACT 3: CRITICAL FAILURE (Red State)")
            logger.info("Injecting CHAOS (Maximum Density / Collision Inevitable)...")
            await session.post(f"{API_URL}/api/v1/sim/control", 
                               json={"action": "start", "config": {"num_agents": 25, "grid_size": 6}})
            
            logger.info(">> WAITING FOR IMPACT...")
            # Let it run until collision logic triggers alerts
            await asyncio.sleep(8)
            
            # 4. Safety Response
            logger.info("\nACT 4: AUTOMATED SAFETY RESPONSE")
            logger.info("Triggering System Pause (Circuit Breaker)...")
            await session.post(f"{API_URL}/api/v1/sim/control", json={"action": "pause"})
            
            logger.info(">> SYSTEM HALTED. Incident contained.")
            logger.info("-----------------------------------")
            logger.info("🎬 DEMO COMPLETE via script.")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_scenario())
