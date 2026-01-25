import sys
import os
import time
import asyncio

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from utils.message_bus import MessageBus

def verify_ux_agent():
    print("Starting UX Verification...")
    start_time = time.time()
    
    # 1. Load Agent
    try:
        agent_cls = AgentRegistry.load_agent("tests.ux_test_plugin.ux_agent", "UXTestAgent")
        if not agent_cls:
            print("FAILED: Could not load agent class.")
            sys.exit(1)
            
        print(f"Agent Class Loaded: {agent_cls.__name__}")
        
    except Exception as e:
        print(f"FAILED: Exception during loading: {e}")
        sys.exit(1)
        
    # 2. Instantiate
    bus = MessageBus()
    agent = agent_cls("ux_tester", bus)
    
    # 3. Process Task
    async def run_task():
        result = await agent.process_task("test_task")
        return result

    result = asyncio.run(run_task())
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Result: {result}")
    
    if result.get("data") == "UX Verified":
        print(f"SUCCESS: Agent created and verified in {duration:.4f} seconds (runtime).")
        print("This confirms the Developer Guide flow works as expected.")
    else:
        print("FAILED: Task result mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    verify_ux_agent()
