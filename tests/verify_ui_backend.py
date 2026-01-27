import subprocess
import time
import sys
import os
import signal
import json
import asyncio
import websockets
import urllib.request
import urllib.error

# Config
PORT = 3000
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"
WS_URL = f"ws://{HOST}:{PORT}/ws/state"

async def test_backend():
    print(f"Starting server on port {PORT}...")
    
    # Redirect output to file to avoid buffer deadlocks
    out_file = open("server_stress_test.log", "w")
    
    # Start server in background
    # We use python -m agent_forge.cli to ensure we use the installed package in the venv
    cmd = [sys.executable, "-m", "agent_forge.cli", "run", "--ui", "--port", str(PORT)]
        
    process = subprocess.Popen(cmd, stdout=out_file, stderr=subprocess.STDOUT)
    
    try:
        # Wait for server
        server_up = False
        print("Waiting for server health check...")
        for i in range(30):
            try:
                # Try fetching docs or status
                with urllib.request.urlopen(f"{BASE_URL}/docs", timeout=1) as response:
                    if response.status == 200:
                        print("Server is up!")
                        server_up = True
                        break
            except Exception:
                time.sleep(1)
                if process.poll() is not None:
                    print("Server process died early!")
                    return False
        
        if not server_up:
            print("Server failed to start in time.")
            return False

        # Test 1: Start Simulation with 50 Agents
        print("Test 1: Start Simulation (50 Agents)...")
        req_data = json.dumps({
            "action": "start",
            "config": {
                "num_agents": 50,
                "grid_size": 20,
                "vertical": "warehouse"
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(f"{BASE_URL}/api/v1/sim/control", data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
                if data.get("status") != "RUNNING" and not data.get("is_running"):
                     # It might return 'STARTED' or similar, check logic
                     print(f"WARNING: Sim status not RUNNING: {data}")
                else:
                    print(f"PASSED (Response: {data})")
        except Exception as e:
            print(f"FAILED: Start request failed: {e}")
            return False

        # Test 2: WebSocket stream
        print("Test 2: WebSocket Stream & Agent Count...")
        try:
            async with websockets.connect(WS_URL) as ws:
                # Consume messages for 5 seconds
                unique_agents = set()
                start_time = time.time()
                message_count = 0
                
                print("Listening for updates...")
                while time.time() - start_time < 5:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        message_count += 1
                        data = json.loads(msg)
                        
                        if data.get("type") == "step":
                             agent_id = data.get("agent_id")
                             if agent_id:
                                 unique_agents.add(agent_id)
                        elif data.get("type") == "snapshot":
                             agents = data.get("data", {})
                             for aid in agents:
                                 unique_agents.add(aid)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"WS Error: {e}")
                        break
                
                print(f"Received {message_count} messages.")
                print(f"Identified {len(unique_agents)} unique agents.")
                
                if len(unique_agents) < 50:
                     print(f"FAILED: Expected 50 agents, got {len(unique_agents)}")
                     return False
                else:
                     print("PASSED")
        except Exception as e:
            print(f"FAILED: WebSocket Connection Failed: {e}")
            return False

        # Test 3: Stop
        print("Test 3: Stop Simulation...")
        req_data = json.dumps({"action": "stop"}).encode('utf-8')
        req = urllib.request.Request(f"{BASE_URL}/api/v1/sim/control", data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                 print("PASSED")
        except Exception as e:
             print(f"FAILED: Stop request failed: {e}")
             return False
             
        return True

    finally:
        print("Killing server...")
        if process:
            process.terminate()
            try:
                 process.wait(timeout=5)
            except:
                 process.kill()
        if out_file:
            out_file.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    with open("test_ui_results.log", "w") as f:
        # Redirect print to file
        sys.stdout = f
        sys.stderr = f
        
        try:
            print("Starting UI Backend Verification...")
            success = asyncio.run(test_backend())
            if success:
                print("\nBackend UI Stress Test PASSED")
                # We exit 0, but process might not flush if we just sys.exit?
                # Rely on with block closing file.
            else:
                print("\nBackend UI Stress Test FAILED")
                sys.exit(1)
        except Exception as e:
            print(f"An error occurred: {e}")
            sys.exit(1)
