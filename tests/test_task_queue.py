import pytest
import asyncio
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

class QueueAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.processed = []
        
    async def process_task(self, task):
        self.processed.append(task)
        
        # Dynamic Insertion Logic
        if task == "A":
            await self.add_task("B")
            
        # Retry Logic
        if task == "Fail_Once":
            if "Fail_Once_Done" not in self.processed:
                self.processed.append("Fail_Once_Done") # Mark as done so next time we don't fail
                await self.add_task("Fail_Once") # Re-queue
                return # Stop processing this instance (simulate failure)

@pytest.mark.asyncio
async def test_fifo_ordering():
    """Verify tasks are processed in order."""
    bus = MessageBus()
    agent = QueueAgent("FIFO-Agent", bus)
    await agent.start()
    
    await agent.add_task(1)
    await agent.add_task(2)
    await agent.add_task(3)
    
    await asyncio.sleep(0.1)
    
    assert agent.processed == [1, 2, 3]
    
    await agent.stop()

@pytest.mark.asyncio
async def test_dynamic_insertion():
    """Verify functionality when a task adds another task."""
    bus = MessageBus()
    agent = QueueAgent("Dynamic-Agent", bus)
    await agent.start()
    
    # Queue: [A, C]
    await agent.add_task("A")
    await agent.add_task("C")
    
    # Process A -> Adds B. Queue becomes [C, B]
    # Process C -> Queue [B]
    # Process B
    
    await asyncio.sleep(0.1)
    
    assert agent.processed == ["A", "C", "B"]
    
    await agent.stop()

@pytest.mark.asyncio
async def test_retry_logic():
    """Verify manual retry (re-queueing) works."""
    bus = MessageBus()
    agent = QueueAgent("Retry-Agent", bus)
    await agent.start()
    
    await agent.add_task("Fail_Once")
    
    await asyncio.sleep(0.1)
    
    # 1. First attempt: adds "Fail_Once_Done" to processed list (marker), requeues "Fail_Once"
    # 2. Second attempt: sees marker, does nothing (simulating success)
    
    # "Fail_Once" should appear twice in the list of attempted tasks (actually my logic above adds it to processed list first)
    # Let's adjust expectation based on implementation:
    # 1. process("Fail_Once") -> appends "Fail_Once" -> appends "Fail_Once_Done" -> re-queues "Fail_Once"
    # 2. process("Fail_Once") -> appends "Fail_Once" -> logic check passes -> done.
    
    expected = ["Fail_Once", "Fail_Once_Done", "Fail_Once"]
    assert agent.processed == expected
    
    await agent.stop()
