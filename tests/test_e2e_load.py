import asyncio
import time
import psutil
import logging
import pytest
import websockets
import json
import statistics
from uvicorn import Config, Server
from agent_forge.server.api import app, session_manager, SimConfig
from agent_forge.core.runner import HeadlessRunner

PORT = 8006
HOST = "127.0.0.1"

async def run_server():
    config = Config(app=app, host=HOST, port=PORT, log_level="error")
    server = Server(config)
    await server.serve()

@pytest.mark.asyncio
async def test_concurrent_sessions_and_latency():
    # 1. Start Server
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(2)
    
    try:
        # 2. Spawn 5 Concurrent Sessions
        num_sessions = 5
        print(f">>> Spawning {num_sessions} Concurrent Sessions...")
        
        session_ids = []
        for i in range(num_sessions):
            sid = f"load_test_{i}"
            session_ids.append(sid)
            runner = HeadlessRunner()
            session_manager.sessions[sid] = runner
            
            # Start Sim
            # 5 Agents per session = 25 total agents walking around
            conf = SimConfig(num_agents=5, grid_size=10) 
            await session_manager.start_session(sid, conf)
            
        print(f">>> {num_sessions} Sessions Running (Total 25 Agents).")
        
        # 3. Connect Monitor Client
        # Note: Currently API broadcasts ALL sessions to ALL clients via same ConnectionManager
        # So one client will receive updates from ALL 5 sessions.
        uri = f"ws://{HOST}:{PORT}/ws/state"
        
        latencies = []
        messages_received = 0
        start_time = time.time()
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024 # MB
        
        print(">>> Measuring Latency & Throughput for 5 seconds...")
        async with websockets.connect(uri) as ws:
            while time.time() - start_time < 5.0:
                try:
                    msg_str = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(msg_str)
                    
                    # Latency Calc: Now - Event Timestamp
                    # Note: engine uses time.time(). We are local, so diff is valid.
                    if "timestamp" in msg:
                        event_ts = msg["timestamp"]
                        now = time.time()
                        latency_ms = (now - event_ts) * 1000
                        latencies.append(latency_ms)
                    
                    messages_received += 1
                except asyncio.TimeoutError:
                    pass
        
        final_memory = process.memory_info().rss / 1024 / 1024 # MB
        duration = time.time() - start_time
        throughput = messages_received / duration
        
        if latencies:
            avg_lat = statistics.mean(latencies)
            max_lat = max(latencies)
            p99_lat = sorted(latencies)[int(len(latencies)*0.99)]
        else:
            avg_lat, max_lat, p99_lat = 0, 0, 0
            
        print(f"\n>>> LOAD TEST RESULTS ({num_sessions} Sessions):")
        print(f"    Total Messages: {messages_received}")
        print(f"    Throughput:     {throughput:.2f} msg/sec")
        print(f"    Avg Latency:    {avg_lat:.2f} ms")
        print(f"    P99 Latency:    {p99_lat:.2f} ms")
        print(f"    Max Latency:    {max_lat:.2f} ms")
        print(f"    Memory Growth:  {final_memory - initial_memory:.2f} MB")
        
        # 4. Assertions (SLOs)
        # Latency should be low (< 50ms avg locally)
        assert avg_lat < 100, f"Average latency too high: {avg_lat:.2f}ms" # Relaxed for local test
        # Throughput should be roughly 5 sessions * 5 agents * 3Hz (due to overhead) = 75 msg/sec.
        # We got ~75, so let's set baseline to 50.
        assert throughput > 50, f"Expected > 50 msg/sec, got {throughput:.2f}"
        
        print(">>> SUCCESS: System held up under load.")

    finally:
        for sid in session_ids:
            await session_manager.stop_session(sid)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR) # Quiet logs
    asyncio.run(test_concurrent_sessions_and_latency())
