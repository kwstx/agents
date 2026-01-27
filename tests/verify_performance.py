
import asyncio
import time
import sys
import os
from contextlib import contextmanager

# Ensure source is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from agent_forge.core.runner import HeadlessRunner

@contextmanager
def timing(label):
    start = time.time()
    yield
    end = time.time()
    print(f"[{label}] Duration: {end - start:.4f}s")

async def run_benchmark(num_agents, steps=50):
    print(f"\n--- BENCHMARK: {num_agents} Agents, {steps} Steps ---")
    runner = HeadlessRunner()
    
    # Setup
    config = {"latency_rate": 0.0} # Pure performance, no artificial latency
    await runner.setup(num_agents=num_agents, grid_size=20, config=config)
    
    # Attach dummy callback to enable sequence counting
    async def dummy_cb(update): pass
    runner.engine.on_step_callback = dummy_cb
    
    # Start
    await runner.start()
    
    # Measure Loop
    start_time = time.time()
    
    # Probing loop to wait for steps
    # Ideally checking engine sequence id
    last_seq = 0
    target_seq = steps * num_agents # Roughly
    
    # Since headless agents run async, we just wait for X seconds and count throughput?
    # Or strict step counting?
    # Let's run for fixed time and count steps.
    
    duration = 5.0 # Run for 5 seconds
    await asyncio.sleep(duration)
    
    # Stop
    await runner.stop()
    
    # Calculate Metrics
    # We need to peek into the engine or logs to know how many steps happened.
    # Runner doesn't expose total steps easily.
    # Let's count via callback hook if possible, or just estimate?
    # Actually, let's look at `runner.engine._sequence_id` if we can.
    
    total_steps = runner.engine._sequence_id
    elapsed = time.time() - start_time
    sps = total_steps / elapsed
    
    print(f"Total Steps: {total_steps}")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Throughput: {sps:.2f} SPS")
    
    if num_agents == 100 and sps < 10:
        print("FAIL: Throughput < 10 SPS for 100 agents")
    else:
        print("PASS: Performance Criteria Met")

async def run_stress_test():
    print(f"\n--- STRESS TEST: 50 Agents, 5% Failure Rate ---")
    runner = HeadlessRunner()
    
    # Config with Chaos
    config = {
        "failure_rate": 0.05, # 5% chance per step to raise exception
        "latency_rate": 0.0
    }
    
    await runner.setup(num_agents=50, grid_size=20, config=config)
    
    try:
        await runner.start()
        
        # Run for 5 seconds
        await asyncio.sleep(5.0)
        
        # Check if still running
        if runner.is_running:
             print("PASS: System survived chaos injection.")
        else:
             print("FAIL: System stopped unexpectedly.")
             
    except Exception as e:
        print(f"FAIL: Unhandled Exception: {e}")
    finally:
        await runner.stop()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(run_benchmark(10))
    loop.run_until_complete(run_benchmark(50))
    loop.run_until_complete(run_benchmark(100))
    
    loop.run_until_complete(run_stress_test())
