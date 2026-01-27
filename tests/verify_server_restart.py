import asyncio
import time
import pytest
import websockets
import subprocess
import requests
import sys
import os

PORT = 8007
HOST = "127.0.0.1"
API_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

def start_server_process():
    # Run the server in a separate process so we can kill it
    cmd = [sys.executable, "-m", "uvicorn", "agent_forge.server.api:app", 
           "--host", HOST, "--port", str(PORT)]
    # Use PYTHONPATH to ensure imports work
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + ";" + os.path.join(os.getcwd(), "src")
    
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def wait_for_server():
    for _ in range(20):
        try:
            requests.get(f"{API_URL}/docs")
            return True
        except:
            time.sleep(0.2)
    return False

@pytest.mark.asyncio
async def test_server_restart():
    proc1 = None
    proc2 = None
    
    try:
        # 1. Start Server A
        print(">>> Starting Server A...")
        proc1 = start_server_process()
        assert wait_for_server()
        
        # 2. Start Sim & Connect
        print(">>> Starting Sim on Server A...")
        requests.post(f"{API_URL}/api/sim/start", json={"num_agents": 2})
        
        print(">>> Connecting Client...")
        async with websockets.connect(WS_URL) as ws:
            msg = await ws.recv() # Get at least one frame
            print(">>> Client Connected & Receiving.")
            
            # 3. KILL Server A
            print(">>> KILLING Server A...")
            proc1.terminate()
            proc1.wait()
            
            # 4. Verify Disconnect
            print(">>> Verifying Client Disconnect...")
            with pytest.raises(websockets.exceptions.ConnectionClosed):
                # We expect the connection to close or error out rapidly
                await ws.recv()
                await ws.recv() # Might have buffered one frame, second should fail
                
        print(">>> Verified: Client disconnected on server death.")
        
        # 5. Start Server B (Restart)
        print(">>> Starting Server B (Restart)...")
        proc2 = start_server_process()
        assert wait_for_server()
        
        # 6. Verify Session GONE (Honesty)
        print(">>> Checking Session State (should be NOT_CREATED)...")
        resp = requests.get(f"{API_URL}/api/sim/status")
        status = resp.json().get("status")
        print(f">>> Status after restart: {status}")
        assert status == "NOT_CREATED"
        
        print(">>> SUCCESS: Server restart behaved cleanly (Clean disconnect + State Reset).")

    finally:
        if proc1 and proc1.poll() is None: proc1.terminate()
        if proc2 and proc2.poll() is None: proc2.terminate()

if __name__ == "__main__":
    asyncio.run(test_server_restart())
