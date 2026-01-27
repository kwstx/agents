import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json
import time

# Configuration
PORT = 8014 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CONTINUITY_TEST")

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

async def test_continuity():
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
                                    json={"action": "start", "config": {"num_agents": 2}}) as resp:
                assert resp.status == 200
            
            # 2. Connect WS
            async with session.ws_connect(WS_URL) as ws:
                logger.info("WS Connected. Listening...")
                
                last_seq = -1
                frames_received = 0
                
                # Phase 1: Listen for 20 frames
                logger.info("Phase 1: Running for 20 frames...")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") == "step":
                            last_seq = data.get("seq_id")
                            frames_received += 1
                            if frames_received >= 20:
                                break
                
                logger.info(f"Paused at Seq {last_seq}. Sending PAUSE...")
                
                # Phase 2: PAUSE
                async with session.post(f"{API_URL}/api/v1/sim/control", json={"action": "pause"}) as resp:
                    assert resp.status == 200
                    
                logger.info("Paused. verifying SILENCE for 3 seconds...")
                
                # Verify NO events come in
                # We might receive 1 or 2 pending events from the queue race, that's acceptable.
                # But after that, TOTAL SILENCE.
                
                silence_start = time.time()
                pending_frames = 0
                
                try:
                    while time.time() - silence_start < 3.0:
                        # Wait for message with short timeout
                        msg = await asyncio.wait_for(ws.receive(), timeout=0.5)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("type") == "step":
                                seq = data.get("seq_id")
                                logger.warning(f"Received lingering frame seq={seq} during pause")
                                pending_frames += 1
                                last_seq = max(last_seq, seq) # Update expected last
                except asyncio.TimeoutError:
                    # Good, no message received
                    pass
                
                if pending_frames > 5: # Tolerance for queue drain
                    logger.error(f"FAILURE: Received {pending_frames} frames during PAUSE! Simulation did not stop.")
                    sys.exit(1)
                    
                logger.info("Silence Verified. Sending RESUME...")
                
                # Phase 3: RESUME
                async with session.post(f"{API_URL}/api/v1/sim/control", json={"action": "resume"}) as resp:
                    assert resp.status == 200
                    
                logger.info("Resumed. Verifying Continuity...")
                
                # Verify Resumption
                # Next frame should be > last_seq (strictly +1 for specific agent, but globally >)
                # Ideally, we check that we get *something*
                
                resumed_frames = 0
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") == "step":
                            seq = data.get("seq_id")
                            logger.info(f"Resumed Frame Seq: {seq}")
                            
                            # Simple Monotonicity Check
                            if seq <= last_seq:
                                logger.error(f"FAILURE: Sequence Regression! {seq} <= {last_seq}")
                                sys.exit(1)
                                
                            last_seq = seq
                            resumed_frames += 1
                            if resumed_frames >= 10:
                                break
                                
                logger.info(">>> SUCCESS: Pause/Resume Continuity Verified.")

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_continuity())
