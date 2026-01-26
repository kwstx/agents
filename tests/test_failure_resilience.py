import asyncio
import httpx
import logging
import pytest
from uvicorn import Config, Server
from agent_forge.server.api import app, session_manager, SimConfig

PORT = 8004 # Unique port
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"

async def run_server():
    config = Config(app=app, host=HOST, port=PORT, log_level="error")
    server = Server(config)
    await server.serve()

@pytest.mark.asyncio
async def test_graceful_failure():
    # 1. Start Server
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(2)
    
    try:
        async with httpx.AsyncClient() as client:
            # 2. Start Simulation
            resp = await client.post(f"{BASE_URL}/api/sim/start", json={
                "num_agents": 2, "grid_size": 10, "vertical": "warehouse"
            })
            assert resp.status_code == 200
            
            # 3. Verify Status is RUNNING
            resp = await client.get(f"{BASE_URL}/api/sim/status")
            state = resp.json()
            assert state["status"] == "RUNNING"
            assert state["is_running"] is True
            
            print(">>> Sim RUNNING. Injecting CRASH...")
            
            # 4. Inject Failure (Simulate SDK Thread Crash)
            # Since we are in same process, we cheat and call internal method
            runner = session_manager.sessions["default"]
            await runner.fail("Simulated Critical Error: Out of Memory")
            
            # 5. Verify Status is FAILED
            resp = await client.get(f"{BASE_URL}/api/sim/status")
            state = resp.json()
            print(f">>> API Reported State: {state}")
            
            assert state["status"] == "FAILED"
            assert state["is_running"] is False
            assert "Simulated Critical Error" in state["error"]
            
            print(">>> SUCCESS: Server correctly reported FAILED status.")
            
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_graceful_failure())
