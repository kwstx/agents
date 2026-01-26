import asyncio
import json
import logging
import pytest
import websockets
from uvicorn import Config, Server
from agent_forge.server.api import app, session_manager, SimConfig

PORT = 8003 # Unique port
HOST = "127.0.0.1"

async def run_server():
    config = Config(app=app, host=HOST, port=PORT, log_level="error")
    server = Server(config)
    await server.serve()

@pytest.mark.asyncio
async def test_ui_death_and_resurrection():
    # 1. Start Server
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(2)
    
    try:
        # 2. Start Simulation
        config = SimConfig(num_agents=5, grid_size=10)
        # Ensure session
        from agent_forge.core.runner import HeadlessRunner
        if "default" not in session_manager.sessions:
            session_manager.sessions["default"] = HeadlessRunner()
            
        await session_manager.start_session("default", config)
        uri = f"ws://{HOST}:{PORT}/ws/state"
        
        last_seq_before_death = 0
        
        # 3. Connect UI (Client A)
        print(">>> Client A: Connecting...")
        async with websockets.connect(uri) as ws_a:
            # Read a few frames
            for _ in range(5):
                msg = await ws_a.recv()
                data = json.loads(msg)
                last_seq_before_death = data.get("seq_id", 0)
                print(f"Client A received seq: {last_seq_before_death}")
        
        print(f">>> Client A: DIED (Disconnect). Last seq: {last_seq_before_death}")
        
        # 4. Simulation Continues Headless
        # We wait 3 seconds. The sim should produce ~30 frames (10Hz).
        print(">>> Simulation running headless for 3 seconds...")
        await asyncio.sleep(3.0)
        
        # 5. Connect UI (Client B - Resurrection)
        print(">>> Client B: Reconnecting...")
        async with websockets.connect(uri) as ws_b:
            msg = await ws_b.recv()
            data = json.loads(msg)
            new_seq = data.get("seq_id", 0)
            print(f"Client B received seq: {new_seq}")
            
            # 6. Verify Progress
            gap = new_seq - last_seq_before_death
            print(f"Gap detected: {gap}")
            
            assert new_seq > last_seq_before_death, "Simulation froze while UI was disconnected!"
            assert gap > 10, f"Simulation didn't progress enough! Only {gap} frames in 3s."
            
        print(">>> SUCCESS: Simulation survived UI death and Client B resynced.")
            
    finally:
        await session_manager.stop_session("default")
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_ui_death_and_resurrection())
