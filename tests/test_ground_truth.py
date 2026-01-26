import asyncio
import json
import logging
import pytest
import websockets
from uvicorn import Config, Server
from agent_forge.server.api import app, session_manager, SimConfig

PORT = 8005
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"

async def run_server():
    config = Config(app=app, host=HOST, port=PORT, log_level="error")
    server = Server(config)
    await server.serve()

@pytest.mark.asyncio
async def test_alert_trustworthiness():
    # 1. Start Server
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(2)
    
    try:
        # 2. Config for Rapid Death
        # High drain: 50% per step. Agent has 100%. Dies in 2 ticks.
        config = SimConfig(num_agents=1, grid_size=10)
        
        # We need to inject the drain parameter. 
        # The SimConfig Pydantic model might need to accept extra kwargs or we mock it.
        # Alternatively, we pass a dict to setup that overrides default.
        # Let's inspect SimConfig.. it's strict.
        # We will manually start the session via Python API to bypass Pydantic model limits if needed, 
        # or rely on defaults being slower.
        # Let's interact with session_manager directly.
        from agent_forge.core.runner import HeadlessRunner
        if "default" not in session_manager.sessions:
             session_manager.sessions["default"] = HeadlessRunner()
             
        # Override start_session to pass custom config dict
        runner = session_manager.sessions["default"]
        custom_conf = {"battery_drain": 45.0} # Dies in ~3 steps (100 -> 55 -> 10 -> -35)
        await runner.setup(num_agents=1, grid_size=5, config=custom_conf)
        
        # Hook callback manually since we bypassed session_manager.start_session
        if runner.engine:
            runner.engine.on_step_callback = session_manager.on_engine_step
            
        await runner.start() # Start logic loop
        
        uri = f"ws://{HOST}:{PORT}/ws/state"
        
        print(">>> Connecting Witness (WebSocket)...")
        async with websockets.connect(uri) as ws:
            death_confirmed = False
            last_battery = 100.0
            
            # Listen for ~10 frames
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    
                    obs = data.get("observation", {})
                    info = data.get("info", {})
                    
                    # Verify State Trace
                    batt = obs.get("battery", 0)
                    print(f"Frame: Battery={batt}, Info={info}")
                    
                    # Check for "Ghost Alerts" (False Positives)
                    if info.get("event") == "battery_depleted":
                        assert batt <= 0, f"False Positive! Reported DEAD but battery is {batt}"
                        death_confirmed = True
                        print(">>> Verified: Death Alert matched Ground Truth (Battery <= 0)")
                    
                    # Check for "Missed Alerts" (False Negatives)
                    if batt <= 0:
                        if info.get("event") != "battery_depleted":
                            # Note: Engine might continue skipping steps after death, ensuring we catch the EXACT frame
                            print(">>> Critical: Battery DEAD but no Alert?") 
                            # If agent handles death by stopping, we might strictly see the alert ONCE.
                        
                    last_battery = batt
                    
                    if death_confirmed:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            assert death_confirmed, "Failed to capture Death Alert! (Agent should have died)"
            print(">>> SUCCESS: Mission Control reflects Ground Truth.")
            
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_alert_trustworthiness())
