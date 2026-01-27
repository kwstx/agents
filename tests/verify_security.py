import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json

# Configuration
PORT = 8017 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SECURITY_TEST")

def start_server_process():
    cmd = [sys.executable, "-m", "uvicorn", "agent_forge.server.api:app", 
           "--host", HOST, "--port", str(PORT)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + ";" + os.path.join(os.getcwd(), "src")
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

async def test_security():
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Starting Attack Vectors...")
        
        async with aiohttp.ClientSession() as session:
            
            # 1. Malformed JSON (Should be 422 Unprocessable Entity)
            logger.info("Test 1: Malformed JSON")
            async with session.post(f"{API_URL}/api/v1/sim/control", data="{ bad_json: }", headers={"Content-Type": "application/json"}) as resp:
                logger.info(f" -> Status: {resp.status}")
                if resp.status != 422 and resp.status != 400:
                    logger.error(f"FAILURE: Malformed JSON accepted or 500. Status: {resp.status}")
                    sys.exit(1)

            # 2. Unknown Action (Should be 400 Bad Request)
            logger.info("Test 2: Unknown Action")
            async with session.post(f"{API_URL}/api/v1/sim/control", json={"action": "explode_server"}) as resp:
                logger.info(f" -> Status: {resp.status}")
                if resp.status != 400:
                    logger.error(f"FAILURE: Unknown action not caught as 400. Status: {resp.status}")
                    sys.exit(1)

            # 3. Semantic Abuse: Negative Agents (Currently might 500 or pass, goal is strict validation)
            logger.info("Test 3: Negative Agents")
            async with session.post(f"{API_URL}/api/v1/sim/config", json={"num_agents": -5}) as resp: # Wrapper
                # Actually usage is via control endpoint
                 pass
            
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start", "config": {"num_agents": -5}}) as resp:
                logger.info(f" -> Status: {resp.status}")
                # We expect this to FAIL safely (400/422). If it starts the sim with -5, that's bad.
                # If API doesn't validate, it might return 200 but crash backend.
                if resp.status == 200:
                     logger.warning(" -> CAUTION: Server accepted negative agents.")
                elif resp.status >= 500:
                     logger.error("FAILURE: Server crashed (500) on negative input.")
                     sys.exit(1)
                else:
                    logger.info(" -> SUCCESS: Server rejected negative input.")

            # 4. Semantic Abuse: Massive Grid (Memory/DoS)
            logger.info("Test 4: Massive Grid Size (10,000)")
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start", "config": {"grid_size": 10000, "num_agents": 1}}) as resp:
                logger.info(f" -> Status: {resp.status}")
                if resp.status == 200:
                    logger.warning(" -> CAUTION: Server accepted massive grid.")
                elif resp.status >= 500:
                    logger.error("FAILURE: Server crashed (500) on massive grid.")
                    sys.exit(1)
                else:
                     logger.info(" -> SUCCESS: Server rejected massive grid.")

            # 5. Invalid Data Type (String for Int)
            logger.info("Test 5: String for Integer field")
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start", "config": {"num_agents": "many"}}) as resp:
                 logger.info(f" -> Status: {resp.status}")
                 if resp.status != 422:
                     logger.error(f"FAILURE: Pydantic failed to reject string for int. Status: {resp.status}")
                     sys.exit(1)
                     
        logger.info(">>> SUCCESS: Security fuzzing complete (some warnings may apply pending strict validation).")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_security())
