import asyncio
import os
import random
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

DB_PATH = "failure_test.db"
LOG_FILE = "failure_test.jsonl"

async def robust_agent(engine, agent_id, target_moves=5):
    """Retries actions until success."""
    print(f"[{agent_id}] Starting (Robust)...")
    success_count = 0
    attempts = 0
    
    while success_count < target_moves and attempts < 20:
        attempts += 1
        try:
            # Try to move RIGHT
            succeeded = await engine.perform_action(agent_id, "RIGHT")
            if succeeded:
                success_count += 1
                print(f"[{agent_id}] Move Success ({success_count}/{target_moves})")
            else:
                print(f"[{agent_id}] Move Failed (Logic)")
        except Exception as e:
            print(f"[{agent_id}] Network Error (Retrying): {e}")
            await asyncio.sleep(0.1)
            
    if success_count == target_moves:
        print(f"[{agent_id}] SUCCESS: Completed task.")
        return True
    else:
        print(f"[{agent_id}] FAILURE: Gave up.")
        return False

async def fragile_agent(engine, agent_id):
    """Crashes on first error."""
    print(f"[{agent_id}] Starting (Fragile)...")
    try:
        # Move UP
        await engine.perform_action(agent_id, "UP")
        print(f"[{agent_id}] Moved UP.")
        # Try invalid action
        await engine.perform_action(agent_id, "INVALID_ACTION")
        print(f"[{agent_id}] Sent Invalid Action.")
        # Trigger frequent error
        await engine.perform_action(agent_id, "RIGHT")
        print(f"[{agent_id}] Moved RIGHT.")
    except Exception as e:
        print(f"[{agent_id}] CRASHED on error: {e}")
        return False # Simulated crash
    
    return True

async def run_verification():
    print("Starting Failure Resilience Verification...")
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    
    # Setup Engine with high failure rate
    env = GridWorld(size=10)
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    # 30% failure rate: High instability
    stress_config = {"failure_rate": 0.3} 
    engine = SimulationEngine(env, logger, stress_config)
    
    # Run concurrent agents
    task_robust = asyncio.create_task(robust_agent(engine, "RobustAgent", 5))
    task_fragile = asyncio.create_task(fragile_agent(engine, "FragileAgent"))
    
    results = await asyncio.gather(task_robust, task_fragile)
    
    robust_ok = results[0]
    fragile_lived = results[1] # Might be False if crashed, which is expected
    
    print("\n--- Results ---")
    print(f"Robust Agent Success: {robust_ok}")
    print(f"Fragile Agent Survived: {fragile_lived}")
    
    # Verification Logic
    if robust_ok:
        print("SUCCESS: Robust agent operated through instability.")
    else:
        print("FAILURE: Robust agent failed to complete task.")
        
    # Check Logs
    conn = logger.get_logs(limit=100) # Reusing helper internal method logic kinda
    # Oops, get_logs is on instance.
    logs = logger.get_logs()
    print(f"Total Logs: {len(logs)}")
    
    # Cleanup
    try:
        os.remove(DB_PATH)
        # os.remove(LOG_FILE) # Keep for inspection
    except:
        pass

if __name__ == "__main__":
    asyncio.run(run_verification())
