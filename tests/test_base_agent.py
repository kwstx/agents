import pytest
import asyncio
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

class MockAgent(BaseAgent):
    """Concrete implementation for testing."""
    async def process_task(self, task):
        if task == "fail":
            raise ValueError("Task failed")
        return f"Processed {task}"

@pytest.mark.asyncio
async def test_agent_initialization():
    bus = MessageBus()
    agent = MockAgent("TestBot", bus)
    
    assert agent.agent_id == "TestBot"
    assert agent.state["status"] == "idle"
    assert agent.message_bus == bus

@pytest.mark.asyncio
async def test_agent_task_processing():
    bus = MessageBus()
    await bus.start()
    agent = MockAgent("Worker", bus)
    await agent.start()
    
    await agent.add_task("task_1")
    
    # Allow loop to process
    await asyncio.sleep(0.1)
    
    # Since we can't easily peek into internal loop state without race conditions,
    # we verify via side effects or by checking queue empty
    assert agent.task_queue.empty()
    assert agent.state["status"] == "active"
    
    await agent.stop()
    await bus.stop()

@pytest.mark.asyncio
async def test_agent_communication():
    bus = MessageBus()
    await bus.start()
    agent = MockAgent("Communicator", bus)
    
    received = []
    async def spy(message):
        received.append(message)
    
    bus.subscribe("outbox", spy)
    
    await agent.send_message("outbox", "hello")
    await asyncio.sleep(0.1)
    
    assert len(received) == 1
    assert received[0].payload == "hello"
    assert received[0].sender == "Communicator"
    
    await bus.stop()
