import pytest
import asyncio
import os
import json
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from utils.memory import Memory

DB_PATH = "tests/data/test_failure.db"

class CrashAgent(BaseAgent):
    """Agent that can be instructed to crash."""
    async def process_task(self, task):
        if task == "crash_now":
            # Simulate critical failure logic
            # This uncaught exception will be caught by BaseAgent._process_tasks 
            # and logged as 'task_error'
            raise ValueError("Simulated Critical System Failure")
            
        self.state["status"] = "working"
        self.log_memory("action", f"Processed {task}")
        self.state["status"] = "idle"

    async def setup_memory(self):
        # Override to use test DB
        if not self.memory_module:
            self.memory_module = Memory(DB_PATH)

async def run_crash_scenario():
    # Setup
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    bus = MessageBus()
    
    # 1. First Run: The Crash
    agent_id = "Phoenix_01"
    agent = CrashAgent(agent_id, bus)
    await agent.start()
    
    await agent.add_task("Work_1")
    await asyncio.sleep(0.1)
    
    # Trigger Crash
    await agent.add_task("crash_now")
    await asyncio.sleep(0.1) 
    
    # Agent is technically still "running" loop but moved to next task after catching error.
    # To simulate a HARD crash/restart, we explicitly stop and destroy object.
    await agent.stop()
    del agent
    
    # 2. Second Run: The Recovery (New Instance, Same ID)
    print("\n--- Simulating Restart ---\n")
    recovered_agent = CrashAgent(agent_id, bus)
    await recovered_agent.start()
    
    await recovered_agent.add_task("Work_After_Recovery")
    await asyncio.sleep(0.1)
    
    await recovered_agent.stop()
    if recovered_agent.memory_module:
        recovered_agent.memory_module.close()

def test_memory_persistence_under_crash():
    asyncio.run(run_crash_scenario())
    
    # Verify Logs
    mem = Memory(DB_PATH)
    logs = mem.query_memory(agent_id="Phoenix_01", limit=100)
    # chronological
    logs.reverse() 
    
    print(f"Total Logs: {len(logs)}")
    for l in logs:
        print(f"LOG: [{l['timestamp']}] {l['type']} -> {l['content']}")
    
    # 1. Verify Pre-Crash Work
    assert any(l["content"] == "Processed Work_1" for l in logs), "Missing Pre-Crash Work"
    
    # 2. Verify Crash Log (task_error)
    # BaseAgent logs error details in 'content' or 'metadata'? 
    # BaseAgent code: self.log_activity("task_error", {"error": str(e)})
    # log_activity calls log_memory("task_error", {"error":...})
    # content will be the dict JSON, or if BaseAgent serializes...
    # memory.py checks if string, else dumps.
    
    crash_log = next((l for l in logs if l["type"] == "task_error"), None)
    assert crash_log is not None, "Memory failed to capture the crash event!"
    
    # Check content for specific error message
    # content is loaded JSON dict if memory.py works as expected
    if isinstance(crash_log["content"], str):
        content_dict = json.loads(crash_log["content"])
    else:
        content_dict = crash_log["content"]
        
    assert "Simulated Critical System Failure" in content_dict["error"]
    
    # 3. Verify Post-Crash Work
    assert any(l["content"] == "Processed Work_After_Recovery" for l in logs), "Missing Post-Recovery Work"
    
    # 4. Verify Continuity
    # Crash log should be after Work_1 and before Work_After_Recovery
    # (Relies on list index order in chronological list)
    idx_work1 = next(i for i, l in enumerate(logs) if l["content"] == "Processed Work_1")
    idx_crash = logs.index(crash_log)
    idx_recov = next(i for i, l in enumerate(logs) if l["content"] == "Processed Work_After_Recovery")
    
    assert idx_work1 < idx_crash < idx_recov, "Temporal ordering of crash is wrong!"
    
    print("\nSUCCESS: Memory faithfully recorded pre-crash, crash, and post-recovery events.")

if __name__ == "__main__":
    test_memory_persistence_under_crash()
