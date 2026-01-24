
import asyncio
import os
import shutil
import sys
import glob
import json
import logging
import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.message_bus import MessageBus
from environments.grid_world import GridWorld
from agents.grid_agent import GridAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrationTest")

async def main():
    logger.info("Starting Integration Test: Agent Runtime + GridWorld")

    # 1. Setup Environment and Infrastructure
    message_bus = MessageBus()
    env = GridWorld(size=5) # 5x5 grid
    
    agent_id = "test_explorer_01"
    
    # Clean previous logs for this agent to ensure clean test
    log_dir = f"logs/checkpoints/{agent_id}"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
        logger.info(f"Cleaned up old logs in {log_dir}")

    # 2. Initialize Agent
    agent = GridAgent(agent_id, message_bus, env)
    await agent.start()
    
    # 3. Assign Task
    task = "navigate_to_goal"
    logger.info(f"Assigning task: {task}")
    await agent.add_task(task)
    
    # 4. Wait for completion
    # In a real scenario we might wait for a specific message or state change.
    # Here we poll the agent status or just wait a fixed time since we know it's fast.
    max_wait = 5.0
    elapsed = 0
    while agent.state["status"] in ["working", "active"] and elapsed < max_wait:
        if agent.state["status"] == "active" and agent.task_queue.empty():
            # If active but no tasks, it might be done (BaseAgent sets status to active after task)
            # But process_task is async, so we need to be careful. 
            # The BaseAgent _process_tasks sets status to 'working' then back to 'active'.
            # If we catch it in 'active' and queue empty, it might be done or waiting.
            # However, our process_task runs the whole episode. So while it's running, status is 'working'.
            # Once it returns, status becomes 'active'.
            # So if we see 'active' again after it was 'working', we are done.
            pass
        
        await asyncio.sleep(0.5)
        elapsed += 0.5
        
    await agent.stop()
    logger.info("Agent stopped.")
    
    # 5. Verification
    logger.info("Verifying results...")
    
    # Check if checkpoints were created
    checkpoints = glob.glob(f"{log_dir}/*.json")
    if not checkpoints:
        logger.error("FAILED: No checkpoints found!")
        sys.exit(1)
        
    logger.info(f"Found {len(checkpoints)} checkpoints.")
    
    # Verify content of the last checkpoint
    checkpoints.sort()
    last_checkpoint_path = checkpoints[-1]
    
    with open(last_checkpoint_path, 'r') as f:
        data = json.load(f)
        
    state = eval(data["state"]) if isinstance(data["state"], str) else data["state"]
    # Note: BaseAgent saves state as str(self.state) in save_checkpoint, 
    # but let's check how it truly behaves. 
    # Looking at base_agent.py: "state": str(self.state)
    # So it is a string representation of the dict.
    
    logger.info(f"Final State in Log: {state}")
    
    # Check if we reached goal (4,4)
    # The string will look like "{'status': 'active', ..., 'current_position': (4, 4), ...}"
    if "'current_position': (4, 4)" in str(state):
        logger.info("SUCCESS: Agent reached target position (4, 4).")
    else:
        logger.error("FAILED: Agent did not reach target position.")
        sys.exit(1)
        
    if "total_reward" in str(state):
         logger.info("SUCCESS: Reward tracking verified.")
    else:
         logger.error("FAILED: Reward tracking missing.")
         sys.exit(1)

    logger.info("Integration Test PASSED.")

if __name__ == "__main__":
    asyncio.run(main())
