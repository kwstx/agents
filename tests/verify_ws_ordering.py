import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json
import pytest

# Configuration
PORT = 8009 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WS_ORDER_TEST")

def start_server_process():
    cmd = [sys.executable, "-m", "uvicorn", "agent_forge.server.api:app", 
           "--host", HOST, "--port", str(PORT)]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + ";" + os.path.join(os.getcwd(), "src")
    # Redirect to avoid cluttering test output
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

async def test_ws_ordering():
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Connecting WS...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Start Sim
            async with session.post(f"{API_URL}/api/v1/sim/control", json={"action": "start"}) as resp:
                assert resp.status == 200
            
            # 2. Connect WS and Listen
            async with session.ws_connect(WS_URL) as ws:
                logger.info("WS Connected. Listening for 50 updates...")
                
                last_seq = -1
                count = 0
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        
                        # Only check 'step' updates which have seq_id
                        if data.get("type") == "step":
                            seq = data.get("seq_id")
                            
                            # Log first few
                            if count < 5:
                                logger.info(f"Received step seq={seq}")
                                
                            if last_seq != -1:
                                # ASSERTION: Monotonic +1
                                if seq != last_seq + 1:
                                    logger.error(f"FAILURE: Sequence Jump! {last_seq} -> {seq}")
                                    sys.exit(1)
                                
                            last_seq = seq
                            count += 1
                            
                            if count >= 50:
                                break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
                        
                logger.info(">>> SUCCESS: Verified 50 sequential frames with no gaps.")
                
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_ws_ordering())
