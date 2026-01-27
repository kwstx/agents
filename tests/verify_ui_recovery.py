import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json

# Configuration
PORT = 8015 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RECOVERY_TEST")

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

async def test_recovery():
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Connecting...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Start Sim
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start"}) as resp:
                assert resp.status == 200
            
            # Allow sim to run and generate some state (e.g. move agents)
            logger.info("Sim running for 2 seconds...")
            await asyncio.sleep(2.0)
            
            # 2. Connect LATE JOINER
            logger.info("Connecting Late Client...")
            async with session.ws_connect(WS_URL) as ws:
                # Expect FIRST message to be 'snapshot'
                msg = await ws.receive() 
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")
                    logger.info(f"First Message Type: {msg_type}")
                    
                    if msg_type != "snapshot":
                        logger.error(f"FAILURE: Expected 'snapshot', got '{msg_type}'")
                        sys.exit(1)
                        
                    snapshot_data = data.get("data")
                    if not snapshot_data or len(snapshot_data) == 0:
                         logger.error("FAILURE: Snapshot is empty!")
                         sys.exit(1)
                         
                    logger.info(f"Snapshot Received: {len(snapshot_data)} agents.")
                    
                    # 3. Simulate RECONNECT
                    logger.info("Simulating Disconnect/Reconnect...")
                    
                # Close and Reconnect
            await asyncio.sleep(0.5)
            
            async with session.ws_connect(WS_URL) as ws2:
                # Expect snapshot again
                msg = await ws2.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")
                    
                    if msg_type == "snapshot":
                         logger.info(">>> SUCCESS: Snapshot received on Reconnect.")
                    else:
                         logger.error(f"FAILURE: Reconnect got '{msg_type}' instead of snapshot.")
                         sys.exit(1)

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_recovery())
