import pytest
import asyncio
import os
import json
import shutil
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

class CheckpointAgent(BaseAgent):
    async def process_task(self, task):
        return f"Processed: {task}"

@pytest.fixture
def clean_checkpoints():
    path = "logs/checkpoints/CheckpointBot"
    if os.path.exists(path):
        shutil.rmtree(path)
    yield
    # Cleanup after test if desired, but keeping them helps manual inspection too

@pytest.mark.asyncio
async def test_checkpoint_creation(clean_checkpoints):
    """Verify that a checkpoint file is created after a task."""
    bus = MessageBus()
    agent = CheckpointAgent("CheckpointBot", bus)
    await agent.start()
    
    await agent.add_task("TestTask_1")
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Verify file existence
    checkpoint_dir = "logs/checkpoints/CheckpointBot"
    assert os.path.exists(checkpoint_dir)
    files = os.listdir(checkpoint_dir)
    assert len(files) >= 1
    
    # Verify Content
    latest_file = os.path.join(checkpoint_dir, files[-1])
    with open(latest_file, "r") as f:
        data = json.load(f)
        
    assert data["agent_id"] == "CheckpointBot"
    assert data["task"] == "TestTask_1"
    assert data["result"] == "Processed: TestTask_1"
    assert "timestamp" in data
    assert "state" in data
    
    await agent.stop()
