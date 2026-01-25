import pytest
import asyncio
import json
import os
import uuid
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

# Mock Agent for testing
class MockAgent(BaseAgent):
    async def process_task(self, task):
        pass

@pytest.mark.asyncio
async def test_message_protocol_structure():
    """Verify that messages have the correct structure and defaults."""
    bus = MessageBus(log_path="logs/test_bus.jsonl")
    await bus.start()
    
    received = []
    async def handler(msg):
        received.append(msg)
        
    bus.subscribe("test_topic", handler)
    
    # Test full message
    trace_id = str(uuid.uuid4())
    await bus.publish("test_topic", "sender_1", "payload_1", 
                      message_type="command", receiver="agent_2", trace_id=trace_id)
    
    await asyncio.sleep(0.1)
    
    assert len(received) == 1
    msg = received[0]
    assert msg.topic == "test_topic"
    assert msg.sender == "sender_1"
    assert msg.payload == "payload_1"
    assert msg.message_type == "command"
    assert msg.receiver == "agent_2"
    assert msg.trace_id == trace_id
    assert msg.timestamp is not None
    
    await bus.stop()

@pytest.mark.asyncio
async def test_message_bus_logging():
    """Verify that messages are logged to file."""
    log_file = "logs/test_bus_logging.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    bus = MessageBus(log_path=log_file)
    await bus.start()
    
    await bus.publish("log_topic", "sender_log", "logging_payload")
    await asyncio.sleep(0.1)
    
    await bus.stop()
    
    assert os.path.exists(log_file)
    
    with open(log_file, "r") as f:
        line = f.readline()
        data = json.loads(line)
        
    assert data["topic"] == "log_topic"
    assert data["sender"] == "sender_log"
    assert data["payload"] == "logging_payload"
    assert "timestamp" in data
    assert "trace_id" in data # Should be auto-generated

@pytest.mark.asyncio
async def test_agent_send_message_updates():
    """Verify BaseAgent can send messages with new fields."""
    bus = MessageBus(log_path="logs/test_agent_bus.jsonl")
    await bus.start()
    
    agent = MockAgent("agent_1", bus)
    await agent.start()
    
    received = []
    bus.subscribe("agent_topic", lambda m: received.append(m))
    
    await agent.send_message("agent_topic", "agent_payload", message_type="response", receiver="target_agent")
    
    await asyncio.sleep(0.1)
    
    assert len(received) == 1
    msg = received[0]
    assert msg.sender == "agent_1" # From agent property
    assert msg.message_type == "response"
    assert msg.receiver == "target_agent"
    
    await agent.stop()
    await bus.stop()
