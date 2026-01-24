import asyncio
import time
import os
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

DB_PATH = "latency_test.db"
LOG_FILE = "latency_test.jsonl"
LATENCY = 0.5  # 500ms

async def test_single_request(engine):
    print("\ntesting single request latency...")
    start = time.time()
    await engine.perform_action("SingleBot", "RIGHT")
    end = time.time()
    duration = end - start
    
    print(f"Recorded duration: {duration:.3f}s")
    if duration < LATENCY:
        print("FAIL: Duration shorter than configured latency.")
        return False
    elif duration > LATENCY * 1.5:
         print("WARNING: Duration significantly longer than latency (overhead?).")
         
    return True

async def test_concurrent_requests(engine):
    print("\ntesting concurrent requests (The Race)...")
    # Reset to known state (though GridWorld doesn't strictly reset pos unless we call reset)
    engine.env.state = (0,0)
    engine._current_observation = (0,0)
    
    start = time.time()
    
    # Launch two agents simultaneously
    # AgentA moves RIGHT -> (1,0)
    # AgentB moves UP -> (0,1)
    # Result if both succeed: (1,1)
    task_a = asyncio.create_task(engine.perform_action("AgentA", "RIGHT"))
    task_b = asyncio.create_task(engine.perform_action("AgentB", "UP"))
    
    await asyncio.gather(task_a, task_b)
    end = time.time()
    
    print(f"Total race duration: {end - start:.3f}s")
    
    # Verify State
    final_state = await engine.get_state("Checker")
    print(f"Final State: {final_state}")
    
    if final_state != (1, 1):
        print(f"FAIL: Race condition corruption? Expected (1,1), got {final_state}")
        # If one overwrote the other based on stale state read, this fails.
        # SimulationEngine logic:
        # await sleep (context switch)
        # perform_action -> calls env.step
        # GridWorld.step uses self.state.
        # Since Python GIL/asyncio is single threaded for the step function, 
        # whoever wakes first modifies state.
        # If A wakes: state (0,0)->(1,0).
        # B wakes: reads (1,0)-> moves UP -> (1,1).
        # So (1,1) is the correct result of serialized updates.
        return False
        
    return True

async def run_verification():
    print("Starting Latency Verification...")
    
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    
    env = GridWorld(size=5)
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    stress_config = {"latency_range": (LATENCY, LATENCY)}
    engine = SimulationEngine(env, logger, stress_config)
    
    single_pass = await test_single_request(engine)
    concurrent_pass = await test_concurrent_requests(engine)
    
    if single_pass and concurrent_pass:
        print("\nSUCCESS: Latency handling verified.")
    else:
        print("\nFAILURE: Latency test failed.")
        
    # Cleanup
    try:
        os.remove(DB_PATH)
        os.remove(LOG_FILE)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(run_verification())
