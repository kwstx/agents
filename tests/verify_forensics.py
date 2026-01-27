import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json
import sqlite3
import time

# Configuration
PORT = 8016 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"
DB_PATH = os.path.abspath("simulation_logs.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FORENSIC_TEST")

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

def analyze_logs(collision_agent_id):
    logger.info(f"--- Forensic Log Analysis for {collision_agent_id} ---")
    logger.info(f"DEBUG: CWD for Test: {os.getcwd()}")
    logger.info(f"DEBUG: Target DB Path: {DB_PATH}")
    
    # Retry waiting for DB to be populated/created
    conn = None
    for k in range(50):
        try:
            if not os.path.exists(DB_PATH):
                if k % 10 == 0: logger.info("Waiting for DB file...")
                time.sleep(0.5)
                continue
                
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Debug: List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            if k % 10 == 0: logger.info(f"DEBUG: Tables found: {tables}")
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interactions'")
            table_exists = cursor.fetchone()
            conn.close()
            
            if table_exists:
                break
            
            time.sleep(0.5)
        except Exception as e:
            if k % 10 == 0: logger.info(f"DB Error: {e}")
            time.sleep(0.5)
            
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get last 5 events for this agent
        cursor.execute('''
            SELECT agent_id, action, state, metadata 
            FROM interactions 
            WHERE agent_id = ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (collision_agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logger.info(f"DEBUG: Rows retrieved for {collision_agent_id}: {len(rows)}")
        for r in rows:
            logger.info(f"DEBUG ROW: {r}")
            
        if not rows:
            logger.error("No logs found for agent!")
            return False
            
        # Look for the collision event
        collision_found = False
        cause_found = False
        
        for i, row in enumerate(rows):
            aid, action, state, meta_json = row
            meta = json.loads(meta_json)
            
            logger.info(f"Event -{i}: Action={action}, State={state[:50]}..., Meta={meta}")
            
            if meta.get("event") == "collision":
                collision_found = True
                logger.info("  -> Collision Event Identified.")
                
                # The CAUSE is usually the action in this same row (if step-based) or previous?
                if action in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    cause_found = True
                    logger.info(f"  -> Cause Identified: Action '{action}' led to collision.")
                else:
                    logger.warning(f"  -> Ambiguous Cause: Action was '{action}'")
                    
        return collision_found and cause_found
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return False

async def test_forensics():
    # Clean DB
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception as e:
            logger.warning(f"Could not remove old DB: {e}")
        
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Connecting...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Start Sim with density to force collision
            # Grid size 4, 6 agents -> High density
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start", "config": {"num_agents": 6, "grid_size": 4}}) as resp:
                assert resp.status == 200
            
            # 2. Monitor for Collision via WS
            async with session.ws_connect(WS_URL) as ws:
                logger.info("Monitoring for Collision...")
                
                collision_agent = None
                
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < 15.0: # Increased timeout
                    try:
                         msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                         if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("type") == "step":
                                info = data.get("info", {})
                                if info.get("event") == "collision":
                                    collision_agent = data.get("agent_id")
                                    logger.info(f"Collision Detected! Agent: {collision_agent}")
                                    break
                    except asyncio.TimeoutError:
                        continue
                        
                if not collision_agent:
                    logger.warning("No collision occurred in time window.")
                    logger.error("FAILURE: Cannot test forensics without a failure event.")
                    sys.exit(1)
                    
                # 3. Analyze Logs
                # Give DB a moment to flush? SQLite is fast but let's be safe
                await asyncio.sleep(1.0)
                
                if analyze_logs(collision_agent):
                    logger.info(">>> SUCCESS: Forensic reconstruction passed.")
                else:
                    logger.error("FAILURE: Forensic analysis failed or ambiguous.")
                    sys.exit(1)

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_forensics())
