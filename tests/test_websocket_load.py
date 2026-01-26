import asyncio
import time
import pytest
import websockets
from agent_forge.server.api import app, session_manager, SimConfig
from agent_forge.core.runner import HeadlessRunner
from uvicorn import Config, Server

# We need a real Async Server running for standard websockets client to connect
# TestClient websocket is okay but mocked. We want real TCP backpressure if possible.
# But spinning up Uvicorn is heavy.
# Let's try to trust TestClient/AsyncClient first? 
# "AsyncClient" doesn't support real network backpressure simulation easily (it's in-memory ASGI).
# To properly test "Backpressure causing blocking", we need Real Sockets.
# So we will launch Uvicorn in a thread/process.

PORT = 8001
HOST = "127.0.0.1"

async def run_server():
    config = Config(app=app, host=HOST, port=PORT, log_level="error")
    server = Server(config)
    await server.serve()

@pytest.mark.asyncio
async def test_websocket_broadcast_load():
    """
    Connects many clients and verifies simulation speed doesn't degrade.
    Includes a SLOW client that reads slowly.
    """
    # 1. Start Server in Background
    # We use a trick: asyncio.create_task for the server
    server_task = asyncio.create_task(run_server())
    
    # Wait for startup
    await asyncio.sleep(2)
    
    try:
        # 2. Start Simulation (via API)
        # We can use httpx or internal manager calls. internal is faster for setup.
        # But we need the server to be running the SAME app instance.
        # The `app` imported here IS the one running.
        
        # Start Session
        config = SimConfig(num_agents=2, grid_size=10)
        
        # Ensure 'default' session exists manually, as the API endpoint would have done
        from agent_forge.core.runner import HeadlessRunner
        if "default" not in session_manager.sessions:
            session_manager.sessions["default"] = HeadlessRunner()
        
        await session_manager.start_session("default", config)
        
        # 3. Connect Clients
        clients = []
        NUM_CLIENTS = 50
        uri = f"ws://{HOST}:{PORT}/ws/state"
        
        # Connect 50 normal clients
        for _ in range(NUM_CLIENTS):
            ws = await websockets.connect(uri)
            clients.append(ws)
            # Start a consumer for each to keep buffer empty-ish
            asyncio.create_task(fast_consumer(ws))
            
        # Connect 1 SLOW client
        slow_ws = await websockets.connect(uri)
        # We do NOT read from it immediately to fill buffer?
        # Or we read very slowly.
        slow_task = asyncio.create_task(slow_consumer(slow_ws))
        
        # 4. Measure Simulation Speed
        # We need to hook into the engine to count steps/sec?
        # Or we just measure time for X messages to arrive at a fast client?
        
        print(f"Connected {NUM_CLIENTS} clients + 1 Slow Client.")
        print("Measuring broadcast latency...")
        
        start_time = time.time()
        # Wait for 5 seconds
        await asyncio.sleep(5)
        duration = time.time() - start_time
        
        # Check logic:
        # If the server blocked on Slow Client, the Fast Clients would stop receiving updates 
        # (or receive them very slowly) because the Engine loop is blocked at "await broadcast".
        
        # We need to know how many steps happened.
        # Let's count messages received by a reference fast client.
        ref_ws = await websockets.connect(uri)
        messages = []
        
        async def counter():
            try:
                while True:
                    msg = await asyncio.wait_for(ref_ws.recv(), timeout=1.0)
                    messages.append(msg)
            except asyncio.TimeoutError:
                pass
        
        # Run counter for 3 seconds
        try:
            await asyncio.wait_for(counter(), timeout=3.0)
        except asyncio.TimeoutError:
            pass # Expected
        
        count = len(messages)
        print(f"Received {count} messages in 3 seconds.")
        
        # Assertions
        # In 3 seconds, assuming Agents run somewhat fast (0.1s sleep loop + overhead), 
        # we expect maybe 10-20 steps per agent? 2 agents -> ~20-40 messages.
        
        assert count > 5, f"Simulation effectively stopped! Only {count} messages."
        
    finally:
        # Cleanup
        await session_manager.stop_session("default")
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

async def fast_consumer(ws):
    try:
        while True:
            await ws.recv() # fast drain
    except:
        pass

async def slow_consumer(ws):
    try:
        while True:
            await ws.recv()
            await asyncio.sleep(1.0) # Slow drain
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_websocket_broadcast_load())
