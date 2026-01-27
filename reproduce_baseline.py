import asyncio
import random
import sys
import os
import shutil
import hashlib
import json
from typing import List, Dict, Any

# Ensure we can import agent_forge
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.runner import HeadlessRunner

SIM_STEPS = 50
NUM_RUNS = 3
SEED = 42

async def run_simulation(run_id: int):
    print(f"--- Starting Run {run_id} ---")
    
    # 1. Set Seed
    random.seed(SEED)
    # If numpy is used/available, seed it too
    try:
        import numpy as np
        np.random.seed(SEED)
    except ImportError:
        pass
        
    # 2. Config to Disable Chaos & Jitter
    config = {
        # Chaos
        "latency_range": (0.0, 0.0), # Disable latency
        "failure_rate": 0.0,         # Disable failures
        "latency_rate": 0.0,         # Disable jitter rate in chaos middleware
        
        # Agent Jitter (Deterministic)
        "start_delay_max": 0.0,      # No start delay
        "step_jitter": 0.0,          # No step jitter
        "step_interval": 0.01,       # Fast fixed interval
        
        # Env
        "battery_drain": 0.5
    }
    
    # Clean up logs to avoid confusion? 
    # Actually, HeadlessRunner uses 'simulation_logs.db'. 
    # We will ignore the DB and capture trace via callback.
    
    runner = HeadlessRunner()
    await runner.setup(num_agents=2, grid_size=10, config=config)
    
    trace: List[Dict] = []
    completion_event = asyncio.Event()
    
    # Hook callback
    async def step_callback(update: Dict[str, Any]):
        # Record essential data
        # We ignore timestamp for comparison
        record = {
            "seq_id": update.get("seq_id"),
            "agent_id": update.get("agent_id"),
            # We hash observation to keep it compact but comparable
            "obs_hash": str(hash(str(update.get("observation")))), 
            # Or just store the obs string if small
            "obs_str": str(update.get("observation")),
            "info": update.get("info")
        }
        trace.append(record)
        
        if len(trace) >= SIM_STEPS:
            if not completion_event.is_set():
                completion_event.set()
    
    runner.engine.on_step_callback = step_callback
    
    # Start
    await runner.start()
    
    # Wait for completion
    try:
        await asyncio.wait_for(completion_event.wait(), timeout=10.0)
    except asyncio.TimeoutError:
        print(f"Run {run_id} Timed Out! (Only got {len(trace)} steps)")
    
    await runner.stop()
    
    print(f"Run {run_id} Completed with {len(trace)} steps recorded.")
    return trace

async def main():
    results = []
    
    for i in range(NUM_RUNS):
        trace = await run_simulation(i+1)
        results.append(trace)
        # Small pause between runs to ensure cleanup
        await asyncio.sleep(1) 
        
    # Compare Results
    baseline = results[0]
    all_match = True
    
    for i, res in enumerate(results[1:]):
        run_num = i + 2
        
        if len(res) != len(baseline):
            print(f"MISMATCH: Run {run_num} has {len(res)} steps, Baseline has {len(baseline)}")
            all_match = False
            continue
            
        for step_idx, (base_step, run_step) in enumerate(zip(baseline, res)):
            # Compare non-timestamp fields
            # Create copies to avoid modifying original data (we want to save duration later)
            base_info = base_step['info'].copy() if base_step['info'] else {}
            run_info = run_step['info'].copy() if run_step['info'] else {}
            
            if 'duration' in base_info: del base_info['duration']
            if 'duration' in run_info: del run_info['duration']
            
            # Construct comparable objects
            base_comp = {**base_step, 'info': base_info}
            run_comp = {**run_step, 'info': run_info}
            
            if base_comp != run_comp:
                print(f"MISMATCH at Step {step_idx}:")
                print(f"  Base: {base_comp}")
                print(f"  Run{run_num}: {run_comp}")
                all_match = False
                break
    
    if all_match:
        print("\nSUCCESS: All runs produced identical traces!")
        
        # Save Golden Run
        with open("golden_run_baseline.json", "w") as f:
            json.dump(baseline, f, indent=2)
        print("Golden Run saved to 'golden_run_baseline.json'")
    else:
        print("\nFAILURE: Runs were not identical.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
