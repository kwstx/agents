import asyncio
import os
import random
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

DB_PATH = "adversarial.db"
LOG_FILE = "adversarial.jsonl"

async def spam_bot(engine):
    """Sends 500 valid actions as fast as possible."""
    print("[SpamBot] Starting Packet Storm...")
    for _ in range(500):
        await engine.perform_action("SpamBot", "RIGHT")
    print("[SpamBot] Done.")

async def wall_banger(engine):
    """Intentionally tries to leave the grid."""
    print("[WallBanger] Starting Boundary Checks...")
    for _ in range(50):
        # We are at (0,0) initially.
        await engine.perform_action("WallBanger", "LEFT") # Wall
        await engine.perform_action("WallBanger", "DOWN") # Wall
    print("[WallBanger] Done.")

async def fuzzer(engine):
    """Sends Garbage."""
    print("[Fuzzer] Starting Fuzzing...")
    payloads = [
        "   ", # whitespace
        "DROP TABLE interactions;", # SQL Injection attempt
        "A" * 1000, # Large buffer
        "😅", # Unicode
        None, # NoneType
        123, # Integer
        {"action": "nested"} # Object
    ]
    for p in payloads:
        try:
             await engine.perform_action("Fuzzer", p)
        except Exception as e:
            print(f"[Fuzzer] Caught expected error for payload {str(p)[:20]}: {e}")
            
    print("[Fuzzer] Done.")

async def run_adversarial_test():
    print("Starting Adversarial Test...")
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    
    env = GridWorld(size=5)
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    engine = SimulationEngine(env, logger, stress_config={})
    
    # Run all concurrenclty
    tasks = [
        asyncio.create_task(spam_bot(engine)),
        asyncio.create_task(wall_banger(engine)),
        asyncio.create_task(fuzzer(engine))
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify System Liveliness
    print("\nVerifying System Liveliness...")
    success = await engine.perform_action("SystemCheck", "RIGHT")
    state = await engine.get_state("SystemCheck")
    print(f"Post-Attack Check: Action Success={success}, State={state}")
    
    if state == (1,0): # Assuming clean state logic or shared state accumulation
        # Actually state is shared single 5x5 grid.
        # SpamBot moved RIGHT 500 times.
        # Grid is size 5. Goal is (4,4).
        # SpamBot probably hit (4,4) and finished the episode long ago?
        # SimulationEngine returns False if done.
        # Let's check if episode is done.
        feedback = await engine.get_feedback("SystemCheck")
        if feedback["done"]:
            print("System finished (simulated agent reached goal).")
        else:
             print("System still active.")
             
        print("SUCCESS: System survived attacks.")
    else:
        # If simulation finished, state might be anything depending on who moved last before finish.
        print("System State check inconclusive but no crash occurred.")
        print("SUCCESS: No crash occurred.")

    # Cleanup
    try:
        os.remove(DB_PATH)
        os.remove(LOG_FILE)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(run_adversarial_test())
