import pytest
import asyncio
import os
import json
from datetime import datetime
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from utils.memory import Memory

DB_PATH = "tests/data/test_replay.db"

class CausalAgent(BaseAgent):
    """Agent that logs state transitions explicitly for replay testing."""
    async def process_task(self, task):
        # 1. Log Intent (Action)
        self.state["status"] = "working"
        self.log_memory("action", f"Starting {task}")
        
        # Simulate work/time passing
        await asyncio.sleep(0.01)
        
        # 2. Log Consequence (Observation/Outcome)
        result = f"{task}_completed"
        self.state["status"] = "idle"
        self.state["last_result"] = result
        
        # Log complex state change as valid JSON in content or metadata
        # Sanitize state (remove datetime objects)
        safe_state = self.state.copy()
        if "last_active" in safe_state:
            safe_state["last_active"] = str(safe_state["last_active"])
            
        self.log_memory("outcome", result, sim_context={"new_state": safe_state})

    async def setup_memory(self):
        # Override to ensure we use the test DB, not the one from settings.yaml
        # This prevents start() from overwriting our injected memory or default path.
        if not self.memory_module:
            self.memory_module = Memory(DB_PATH)

async def run_causal_scenario():
    # Setup
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # We need to inject the custom DB path into the agent.
    # BaseAgent loads from settings.yaml by default.
    # We will override the memory_module manually after init for this test.
    
    bus = MessageBus()
    agent = CausalAgent("TimeKeeper", bus)
    
    # Manually Inject Memory with our test path
    agent.memory_module = Memory(DB_PATH)
    
    await agent.start()
    
    # Step 1
    await agent.add_task("Task_A")
    await asyncio.sleep(0.2) 
    
    # Step 2
    await agent.add_task("Task_B")
    await asyncio.sleep(0.2)
    
    await agent.stop()
    agent.memory_module.close()

def test_causal_replay():
    # 1. Run the scenario
    asyncio.run(run_causal_scenario())
    
    # 2. Inspect Logs
    mem = Memory(DB_PATH)
    logs = mem.query_memory(agent_id="TimeKeeper", limit=100)
    # query returns DESC (newest first). Reverse to get chronological playback.
    logs.reverse()
    
    print(f"\nTotal Logs: {len(logs)}")
    for l in logs:
        print(f"DEBUG LOG: {l['type']} - {l['content']}")
    
    # 3. Verify Monotonic Time & Causal Chain
    # Expected Chain:
    # - task_started (from BaseAgent) -> Task_A
    # - action (from CausalAgent) -> Starting Task_A
    # - outcome (from CausalAgent) -> Task_A_completed
    # - task_completed (from BaseAgent)
    # ... repeat for Task_B
    
    assert len(logs) >= 8 # 4 events per task * 2 tasks
    
    last_timestamp = ""
    reconstructed_state = {"status": "unknown", "last_result": None}
    
    for i, log in enumerate(logs):
        ts = log["timestamp"]
        typ = log["type"]
        content = log["content"]
        ctx = log["sim_context"]
        
        print(f"[{ts}] {typ}: {content}")
        
        # Check Time Monotonicity
        if last_timestamp:
            assert ts >= last_timestamp, f"Time regression at index {i}: {ts} < {last_timestamp}"
        last_timestamp = ts
        
        # Reconstruct State
        # In our CausalAgent, "outcome" logs contain the state snapshot in sim_context
        if typ == "outcome":
            if ctx and "new_state" in ctx:
                new_state = ctx["new_state"]
                reconstructed_state["status"] = new_state.get("status")
                reconstructed_state["last_result"] = new_state.get("last_result")
    
    # 4. Verify Final Reconstructed State matches logic
    assert reconstructed_state["status"] == "idle"
    assert reconstructed_state["last_result"] == "Task_B_completed"
    
    print("\nState Reconstruction Successful: Matches expected final state.")

if __name__ == "__main__":
    test_causal_replay()
