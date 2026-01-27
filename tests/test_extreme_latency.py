import asyncio
import time
import psutil
import os
import sys
import statistics
from typing import Dict, Any, List

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.runner import HeadlessRunner

SIM_STEPS = 100
NUM_AGENTS = 4
GRID_SIZE = 10

process = psutil.Process(os.getpid())

async def run_scenario(name: str, latency_config: Dict[str, Any]):
    print(f"\n--- Starting Scenario: {name} ---")
    print(f"Config: {latency_config}")
    
    # Measure baseline memory
    mem_before = process.memory_info().rss / 1024 / 1024 # MB
    
    config = {
        "enabled": True,
        **latency_config,
        # Ensure agent jitter is zero to isolate network latency comparison
        "start_delay_max": 0.0,
        "step_jitter": 0.0,
        "step_interval": 0.01 # Fast internal tick
    }
    
    runner = HeadlessRunner()
    await runner.setup(num_agents=NUM_AGENTS, grid_size=GRID_SIZE, config=config)
    
    collision_count = 0
    step_count = 0
    start_time = time.time()
    
    completion_event = asyncio.Event()

    async def step_callback(update: Dict[str, Any]):
        nonlocal collision_count, step_count
        step_count += 1
        
        # Check for collision/blocked event
        if update.get("info", {}).get("event") == "blocked":
            collision_count += 1
            
        if step_count >= SIM_STEPS * NUM_AGENTS: # Approx total steps
            if not completion_event.is_set():
                completion_event.set()

    runner.engine.on_step_callback = step_callback
    
    await runner.start()
    
    try:
        # Timeout safety
        await asyncio.wait_for(completion_event.wait(), timeout=60.0)
    except asyncio.TimeoutError:
        print(f"[{name}] TIMEOUT! Simulation stalled.")
    
    duration = time.time() - start_time
    await runner.stop()
    
    mem_after = process.memory_info().rss / 1024 / 1024 # MB
    mem_growth = mem_after - mem_before
    
    print(f"[{name}] Completed in {duration:.2f}s")
    print(f"[{name}] Collisions: {collision_count}")
    print(f"[{name}] Memory Growth: {mem_growth:.2f} MB")
    
    return {
        "collisions": collision_count,
        "duration": duration,
        "mem_growth": mem_growth
    }

async def main():
    # 1. Baseline
    baseline_res = await run_scenario("Baseline (0s Latency)", {
        "jitter_rate": 0.0,
        "latency_range": (0.0, 0.0)
    })
    
    # 2. Extreme Latency
    # 100ms - 200ms latency on EVERY action (rate=1.0)
    extreme_res = await run_scenario("Extreme (0.1-0.2s Latency)", {
        "jitter_rate": 1.0,
        "latency_range": (0.1, 0.2)
    })
    
    print("\n--- Results Summary ---")
    print(f"Baseline Collisions: {baseline_res['collisions']}")
    print(f"Extreme Collisions:  {extreme_res['collisions']}")
    
    # Assertions
    # We expect Extreme to be SLOWER
    assert extreme_res['duration'] > baseline_res['duration']
    
    # We expect Extreme to have MORE or EQUAL collisions 
    # (Stale state leads to two agents moving to same spot thinking it's free)
    if extreme_res['collisions'] > baseline_res['collisions']:
        print("CONFIRMED: Extreme latency caused increased collision rate (Stale State).")
    else:
        print("NOTE: Collision rate did not increase. Agents might be robust or density too low.")
        
    # Stability Check
    if extreme_res['mem_growth'] > 50: # Arbitrary high threshold
        print("WARNING: High memory growth detected!")
    else:
        print("STABILITY: Memory usage within limits.")

if __name__ == "__main__":
    asyncio.run(main())
