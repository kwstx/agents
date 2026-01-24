import asyncio
import os
import sqlite3
import random
import ast
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

DB_PATH = "replay_test.db"
LOG_FILE = "replay_test.jsonl"

async def generate_logs():
    print("generating logs...")
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    
    random.seed(999) # Deterministic generation
    env = GridWorld(size=5)
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    engine = SimulationEngine(env, logger, stress_config={})
    agent_id = "ReplayBot"
    
    actions = ["RIGHT", "RIGHT", "UP", "UP", "LEFT"]
    for action in actions:
        await engine.perform_action(agent_id, action)
        
    print("Logs generated.")

async def verify_replay():
    print("Starting Replay Verification...")
    
    # 1. Read Logs
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT action, state, state_hash FROM interactions ORDER BY id ASC")
    logs = cursor.fetchall()
    conn.close()
    
    # 2. Replay
    # Replay means: Starting from INITIAL state (known 0,0), apply actions and verify resulting state matches log.
    env = GridWorld(size=5)
    # Note: We use engine just for perform_action logic, but we don't need logging/stress
    # But wait, perform_action updates state. 
    # We need to ensure we start at same same initial state. GridWorld init is (0,0).
    
    print(f"Loaded {len(logs)} steps to replay.")
    
    for i, (action, logged_state_str, logged_hash) in enumerate(logs):
        step = i + 1
        
        # Parse logged state (it's a string tuple "(x, y)")
        try:
            logged_state = ast.literal_eval(logged_state_str)
        except:
             # handle complex objects if needed, for tuple it's fine
             logged_state = logged_state_str
             
        # Perform Action
        # Note: GridWorld is deterministic. Stress testing in engine only delays/fails, 
        # but if we successfully logged a state transition, that transition is valid.
        
        # Manually step the env to replicate SimulationEngine logic without the overhead
        obs, _, _, _ = env.step(action)
        
        # Verify
        replayed_state = obs
        replayed_hash = str(hash(str(replayed_state)))
        
        print(f"Step {step}: Action {action} -> Rep {replayed_state} / Log {logged_state}")
        
        if replayed_state != logged_state:
            print(f"FATAL: State mismatch at step {step}!")
            print(f"Expected: {logged_state}")
            print(f"Got:      {replayed_state}")
            exit(1)
            
        if replayed_hash != logged_hash:
            print(f"FATAL: Hash mismatch at step {step}!")
            print(f"Expected: {logged_hash}")
            print(f"Got:      {replayed_hash}")
            exit(1)
            
    print("SUCCESS: Replay matched logs perfectly.")
    
    # Cleanup
    try:
        os.remove(DB_PATH)
        os.remove(LOG_FILE)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(generate_logs())
    asyncio.run(verify_replay())
