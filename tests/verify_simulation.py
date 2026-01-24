import asyncio
import os
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

async def run_verification():
    print("Starting Verification...")
    
    # 1. Setup
    env = GridWorld(size=5)
    logger = InteractionLogger(db_path="test_sim.db", log_file="test_sim.jsonl")
    
    # Stress config: 100ms delay, 0% failure (to keep deterministic for initial check)
    stress_config = {"latency_range": (0.1, 0.12), "failure_rate": 0.0}
    
    engine = SimulationEngine(env, logger, stress_config)
    agent_id = "TestAgent-007"
    
    # 2. Run Loop
    print(f"Initial State: {await engine.get_state(agent_id)}")
    
    actions = ["RIGHT", "RIGHT", "UP", "UP", "LEFT"] # Just some moves
    for action in actions:
        start_time = asyncio.get_running_loop().time()
        
        success = await engine.perform_action(agent_id, action)
        feedback = await engine.get_feedback(agent_id)
        
        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time
        
        print(f"Action: {action}, Success: {success}, Reward: {feedback['reward']}, Duration: {duration:.3f}s")
        
        # Verify latency
        if duration < 0.1:
            print("ERROR: Latency simulation failed!")
            
    # 3. specific Stress Test (high failure)
    print("\nTesting Failure Mode...")
    engine.stress_config["failure_rate"] = 1.0 # 100% fail
    try:
        await engine.perform_action(agent_id, "RIGHT")
        print("ERROR: Should have failed!")
    except Exception as e:
        print(f"Caught expected error: {e}")

    # 4. Verify Logs
    print("\nVerifying Logs...")
    logs = logger.get_logs(agent_id)
    print(f"Found {len(logs)} log entries.")
    if len(logs) < 5:
        print("ERROR: Logging might be missing entries.")
    else:
        print("Logging seems correct.")

    # Cleanup
    try:
        os.remove("test_sim.db")
        os.remove("test_sim.jsonl")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(run_verification())
