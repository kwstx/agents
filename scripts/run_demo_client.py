import logging
import sys
import json
import time
import urllib.request
import urllib.error

# Configuration
PORT = 8018
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("DEMO_CLIENT")

def post_json(endpoint, data):
    url = f"{API_URL}{endpoint}"
    req = urllib.request.Request(url, method="POST")
    req.add_header('Content-Type', 'application/json')
    body = json.dumps(data).encode('utf-8')
    try:
        with urllib.request.urlopen(req, data=body) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error {e.code}: {e.reason}")
        raise e
    except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        raise e

def run_scenario():
    logger.info("🎬 CONNECTING TO EXECUTIVE DEMO SERVER (Sync Mode)")
    
    # Check connection
    try:
        urllib.request.urlopen(f"{API_URL}/docs")
    except Exception as e:
        logger.error(f"Could not connect to server: {e}")
        return

    # 1. Start Phase: NORMAL OPERATIONS
    logger.info("ACT 1: NORMAL OPERATIONS (Green State)")
    logger.info("Starting fleet with optimized density...")
    post_json("/api/v1/sim/control", {"action": "start", "config": {"num_agents": 6, "grid_size": 10}})
    
    logger.info(">> System running smoothly. Agents performing tasks.")
    time.sleep(5)
    
    # 2. Start Phase: DEGRADATION (Increased Load)
    logger.info("\nACT 2: SYSTEM DEGRADATION (Yellow State)")
    logger.info("Injecting load spike (Restarting with High Density)...") 
    post_json("/api/v1/sim/control", {"action": "start", "config": {"num_agents": 12, "grid_size": 8}})
    
    logger.info(">> Congestion increasing. Risk score should be rising.")
    time.sleep(5)
    
    # 3. Start Phase: FAILURE (Red State)
    logger.info("\nACT 3: CRITICAL FAILURE (Red State)")
    logger.info("Injecting CHAOS (Maximum Density / Collision Inevitable)...")
    post_json("/api/v1/sim/control", {"action": "start", "config": {"num_agents": 25, "grid_size": 6}})
    
    logger.info(">> WAITING FOR IMPACT...")
    time.sleep(8)
    
    # 4. Safety Response
    logger.info("\nACT 4: AUTOMATED SAFETY RESPONSE")
    logger.info("Triggering System Pause (Circuit Breaker)...")
    post_json("/api/v1/sim/control", {"action": "pause"})
    
    logger.info(">> SYSTEM HALTED. Incident contained.")
    logger.info("-----------------------------------")
    logger.info("🎬 DEMO COMPLETE via script.")

if __name__ == "__main__":
    run_scenario()
