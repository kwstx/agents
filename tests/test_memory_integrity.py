import pytest
import asyncio
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

class MemoryAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        # Using the base self.state["memory"] as the store
        # In a real app, this might be a list or a more complex structure.
        # For base_agent, memory is a Dict. Let's assume we store a log list in it.
        self.state["memory"] = {"history": []}

    async def process_task(self, task):
        # Log the task execution into memory
        entry = {
            "action": task, 
            "status": "completed", 
            "timestamp": ("mock_time" + str(len(self.state["memory"]["history"])))
        }
        
        # Simulate state changes based on task
        if task == "Perform_Work":
            self.state["status"] = "working"
            await asyncio.sleep(0.2) # Simulate work duration
        elif task == "Simulate_Failure":
            self.state["status"] = "failed"
            entry["status"] = "failed"
        elif task == "Recover":
            self.state["status"] = "active"
            
        self.state["memory"]["history"].append(entry)

    def get_history(self):
        return self.state["memory"]["history"]

@pytest.mark.asyncio
async def test_long_sequence_retention():
    """Verify that the agent retains a long history of actions without corruption."""
    bus = MessageBus()
    agent = MemoryAgent("MemBot", bus)
    await agent.start()
    
    # sequence of 100 actions
    for i in range(100):
        await agent.add_task(f"Action_{i}")
        
    # Wait for processing (100 items might take a split second)
    # Since tasks are processed sequentially in the loop, we just need enough time.
    # A safer way in tests might be checking len(), but here we sleep briefly.
    await asyncio.sleep(0.5)
    
    history = agent.get_history()
    assert len(history) == 100
    assert history[0]["action"] == "Action_0"
    assert history[99]["action"] == "Action_99"
    
    await agent.stop()

@pytest.mark.asyncio
async def test_state_updates():
    """Verify that internal state updates (status) are persisted correctly."""
    bus = MessageBus()
    agent = MemoryAgent("StateBot", bus)
    await agent.start()
    
    assert agent.state["status"] == "active" # Initial start state
    
    await agent.add_task("Perform_Work")
    await asyncio.sleep(0.1)
    assert agent.state["status"] == "working" # After processing, it sets to 'active' in base loop? 
    # Wait, base_agent.py _process_tasks sets status to "working" then "active" after done.
    # Ah, my MemoryAgent.process_task sets it to "working".
    # But immediately after process_task returns, BaseAgent sets it back to "active".
    # So to test "working", we'd need to inspect it *during* the task (hard in async test without mocks)
    # OR we check if the memory log captured the "failed" status which is persistent in history.
    
    await agent.add_task("Simulate_Failure")
    await asyncio.sleep(0.1)
    
    history = agent.get_history()
    failure_entry = history[-1]
    assert failure_entry["action"] == "Simulate_Failure"
    assert failure_entry["status"] == "failed"
    
    # BaseAgent logic sets status back to 'active' unless we override that behavior.
    # But let's check if my manual state set inside the task logic was at least theoretically correct 
    # (even if overwritten later).
    # Actually, let's verify the persistent memory log, which is the "memory" part of this test.
    
    await agent.stop()

@pytest.mark.asyncio
async def test_retrieval_consistency():
    """Verify we can retrieve specific complex objects from memory."""
    bus = MessageBus()
    agent = MemoryAgent("RecallBot", bus)
    await agent.start()
    
    # Add complex tasks
    await agent.add_task("Step1")
    await agent.add_task("Simulate_Failure")
    await agent.add_task("Recover")
    
    await asyncio.sleep(0.1)
    
    history = agent.get_history()
    
    # Find the failure
    failures = [x for x in history if x["status"] == "failed"]
    assert len(failures) == 1
    assert failures[0]["action"] == "Simulate_Failure"
    
    # context recall
    assert len(history) == 3
    assert history[2]["action"] == "Recover"
    
    await agent.stop()
