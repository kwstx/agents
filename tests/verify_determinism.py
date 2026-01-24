import asyncio
import random
import json
import copy
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine

async def run_scenario(seed: int, run_id: str):
    print(f"[{run_id}] Starting run with seed {seed}...")
    
    # 1. Seed Randomness
    random.seed(seed)
    
    # 2. Setup (Deterministic Config)
    # We include stress config to verify that even the random failures/delays are deterministic given the seed.
    stress_config = {
        "latency_range": (0.01, 0.05), 
        "failure_rate": 0.2  # 20% chance of failure to test reproducibility of chaos
    }
    env = GridWorld(size=5)
    # Pass None for logger to avoid file I/O noise, we capture trace in memory
    engine = SimulationEngine(env, logger=None, stress_config=stress_config)
    agent_id = "Agent-Det"
    
    trace = []
    
    # 3. Action Sequence
    actions = ["RIGHT", "RIGHT", "UP", "UP", "LEFT", "DOWN", "RIGHT", "RIGHT"]
    
    # Initial State
    try:
        initial_state = await engine.get_state(agent_id)
        trace.append({"step": "init", "state": copy.deepcopy(initial_state)})
    except Exception as e:
        trace.append({"step": "init", "error": str(e)})
    
    for i, action in enumerate(actions):
        try:
            # Attempt action
            success = await engine.perform_action(agent_id, action)
            
            # Capture feedback
            if success:
                feedback = await engine.get_feedback(agent_id)
                new_state = await engine.get_state(agent_id)
                
                step_data = {
                    "step": i,
                    "action": action,
                    "success": True,
                    "reward": feedback["reward"],
                    "done": feedback["done"],
                    "info": feedback["info"],
                    "state": copy.deepcopy(new_state)
                }
            else:
                # E.g. game over or previous failure
                step_data = {
                    "step": i,
                    "action": action,
                    "success": False,
                    "note": "Action failed or episode done"
                }

        except Exception as e:
            # Capture simulated failures
            step_data = {
                "step": i,
                "action": action,
                "success": False,
                "error": str(e)
            }
            
        trace.append(step_data)
        
    print(f"[{run_id}] Completed with {len(trace)} trace events.")
    return trace

async def verify_determinism():
    SEED = 12345
    
    print("--- RUN 1 ---")
    trace1 = await run_scenario(SEED, "Run1")
    
    print("\n--- RUN 2 ---")
    trace2 = await run_scenario(SEED, "Run2")
    
    print("\n--- COMPARISON ---")
    # Convert to JSON for reliable deep comparison
    json1 = json.dumps(trace1, sort_keys=True, indent=2)
    json2 = json.dumps(trace2, sort_keys=True, indent=2)
    
    if json1 == json2:
        print("SUCCESS: Traces are identical.")
        print("Determinism Verified.")
    else:
        print("FAILURE: Traces differ!")
        print("Diffing not implemented but check outputs.")
        # Simple diff print
        lines1 = json1.splitlines()
        lines2 = json2.splitlines()
        for i, (l1, l2) in enumerate(zip(lines1, lines2)):
            if l1 != l2:
                print(f"Mismatch at line {i}:")
                print(f"Run1: {l1}")
                print(f"Run2: {l2}")
                break

if __name__ == "__main__":
    asyncio.run(verify_determinism())
