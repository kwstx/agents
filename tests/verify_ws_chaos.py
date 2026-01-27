import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json
import pytest

# Configuration
PORT = 8010 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WS_CHAOS_TEST")

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

async def test_ws_chaos():
    """
    Simulates a SLOW client to force the server's output queue (max 100) to fill up.
    We verify that:
    1. The server drops messages.
    2. The client detects the GAP in sequence IDs.
    """
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Connecting WS...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Start Sim - FAST!
            # We want to generate > 100 frames quickly.
            # Assuming sim runs fast enough or we can tweak config.
            # Default is "headless" which is fast.
            async with session.post(f"{API_URL}/api/v1/sim/control", json={"action": "start"}) as resp:
                assert resp.status == 200
            
            # 2. Connect
            async with session.ws_connect(WS_URL) as ws:
                logger.info("WS Connected. Inducing Lag...")
                
                last_seq = -1
                gaps_detected = 0
                received_count = 0
                
                # SLEEP to allow server queue to fill
                # Server queue is 100. Sim generates frames.
                # If we listen but don't read fast enough? 
                # Actually, 'async for msg in ws' reads as fast as possible.
                # We need to explicitly delay the processing loop or not read at all for a bit.
                
                # Testing Strategy:
                # 1. Read first frame.
                # 2. Sleep 2 seconds (Server should produce > 100 frames in 2s if running uncapped).
                # 3. Resume reading.
                # 4. Check for gaps.
                
                msg = await ws.receive() # Read one to confirm connection
                if msg.type == aiohttp.WSMsgType.TEXT:
                     data = json.loads(msg.data)
                     if data.get("type") == "step":
                         last_seq = data.get("seq_id")
                         logger.info(f"Initial Seq: {last_seq}")
                
                logger.info(">>> Pausing Client for 6.0s (Simulating Network Stall)...")
                await asyncio.sleep(6.0) 
                logger.info(">>> Resuming Client...")
                
                # Now drain the socket
                # We expect to see a jump in sequence IDs because the server queue (100) overflowed.
                
                frames_after_pause = 0
                while frames_after_pause < 50:
                    try:
                        # Use timeout to avoid hanging if server stopped
                        msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                    except asyncio.TimeoutError:
                        break
                        
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") == "step":
                            seq = data.get("seq_id")
                            
                            if last_seq != -1:
                                delta = seq - last_seq
                                if delta > 1:
                                    logger.warning(f"GAP DETECTED: {last_seq} -> {seq} (Missed {delta-1} frames)")
                                    gaps_detected += 1
                                    
                            last_seq = seq
                            frames_after_pause += 1
                    else:
                        break
                        
                if gaps_detected > 0:
                    logger.info(f">>> SUCCESS: Verified {gaps_detected} gap events due to congestion.")
                else:
                    logger.warning(">>> NO GAPS DETECTED. Server might be too slow or Queue too large.")
                    # This is technically a failure of the test setup to induce chaos, 
                    # OR the server is blocking on the queue (which would be bad for performance).
                    # 'api.py' uses queue.put_nowait() so it definitely drops.
                    # It means we didn't wait long enough or sim is too slow.
                    sys.exit(1) 

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_ws_chaos())
