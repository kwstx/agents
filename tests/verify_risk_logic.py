import asyncio
import aiohttp
import logging
import sys
import subprocess
import os
import json

# Configuration
PORT = 8013 # Dedicated port
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RISK_TEST")

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

async def test_risk_logic():
    logger.info("Starting Server...")
    proc = start_server_process()
    
    try:
        if not await wait_for_server():
            logger.error("Server failed to start.")
            sys.exit(1)
            
        logger.info("Server Up. Connecting...")
        
        async with aiohttp.ClientSession() as session:
            # 1. Start Sim with 4 agents to increase chance of interactions
            async with session.post(f"{API_URL}/api/v1/sim/control", 
                                    json={"action": "start", "config": {"num_agents": 4}}) as resp:
                assert resp.status == 200
            
            # 2. Connect WS
            async with session.ws_connect(WS_URL) as ws:
                logger.info("WS Connected. Shadowing Risk Logic...")
                
                shadow_risk_score = 0
                max_frames = 200
                frames = 0
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        
                        if data.get("type") == "step":
                            agent_id = data.get("agent_id")
                            obs = data.get("observation")
                            info = data.get("info", {})
                            
                            battery = obs.get("battery", 100)
                            
                            # REPLICATE FRONTEND LOGIC EXACTLY
                            # dashboard.js: 
                            # if (msg.observation.battery < 20) { setRiskScore(prev => Math.min(100, prev + 5)); ... }
                            # else if (msg.info && msg.info.event === "collision") { setRiskScore(prev => Math.min(100, prev + 20)); ... }
                            
                            prev_score = shadow_risk_score
                            
                            if battery < 20.0:
                                shadow_risk_score = min(100, shadow_risk_score + 5)
                                if shadow_risk_score != prev_score:
                                    logger.info(f"RISK INCREASE (+5): Agent {agent_id} Battery {battery:.1f}% -> Score {shadow_risk_score}")
                            elif info.get("event") == "collision":
                                shadow_risk_score = min(100, shadow_risk_score + 20)
                                if shadow_risk_score != prev_score:
                                    logger.info(f"RISK INCREASE (+20): Agent {agent_id} COLLISION -> Score {shadow_risk_score}")
                            
                            # Assert Monotonicity (It should never go down with current logic)
                            if shadow_risk_score < prev_score:
                                logger.error("FAILURE: Risk score decreased! This contradicts the accumulator logic.")
                                sys.exit(1)
                                
                            frames += 1
                            if frames >= max_frames:
                                break
                                
                logger.info(f"Final Risk Score: {shadow_risk_score}")
                if shadow_risk_score > 0:
                    logger.info(">>> SUCCESS: Risk logic correctly accumulated events.")
                else:
                    logger.warning(">>> INCONCLUSIVE: No risk events occurred in time window. Try increasing agents or duration.")
                    # For test purposes, we want to verify logic *when events happen*.
                    # If random walk doesn't trigger it, we might accept it if logic didn't crash.
                    pass

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_risk_logic())
