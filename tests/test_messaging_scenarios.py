import pytest
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any
from utils.message_bus import MessageBus

# --- Helper Objects ---
@dataclass
class CustomPayload:
    id: int
    data: str

# --- Tests ---

@pytest.mark.asyncio
async def test_diverse_payload_types():
    """Verify that the bus handles Dictionaries, Lists, Primitives, and Custom Objects correctly."""
    bus = MessageBus()
    await bus.start()
    
    received = {}
    
    async def handler(msg):
        received[msg.topic] = msg.payload
        
    bus.subscribe("dict_topic", handler)
    bus.subscribe("list_topic", handler)
    bus.subscribe("obj_topic", handler)
    bus.subscribe("int_topic", handler)
    
    # Send diverse data
    payload_dict = {"key": "value", "nested": 1}
    payload_list = [1, 2, "three"]
    payload_obj = CustomPayload(id=99, data="secret")
    payload_int = 42
    
    await bus.publish("dict_topic", "tester", payload_dict)
    await bus.publish("list_topic", "tester", payload_list)
    await bus.publish("obj_topic", "tester", payload_obj)
    await bus.publish("int_topic", "tester", payload_int)
    
    await asyncio.sleep(0.1)
    
    assert received["dict_topic"] == payload_dict
    assert received["list_topic"] == payload_list
    assert received["obj_topic"] == payload_obj
    assert received["int_topic"] == payload_int
    
    await bus.stop()

@pytest.mark.asyncio
async def test_topic_isolation():
    """Verify strictly that agents do not receive messages for topics they aren't subscribed to."""
    bus = MessageBus()
    await bus.start()
    
    inbox_a = []
    inbox_b = []
    
    async def handler_a(msg): inbox_a.append(msg)
    async def handler_b(msg): inbox_b.append(msg)
    
    bus.subscribe("topic-A", handler_a)
    bus.subscribe("topic-B", handler_b)
    
    # Broadcast
    await bus.publish("topic-A", "sender", "Msg for A")
    await bus.publish("topic-B", "sender", "Msg for B")
    await bus.publish("topic-C", "sender", "Msg for nobody") # Should be dropped/ignored
    
    await asyncio.sleep(0.1)
    
    # Check Inbox A
    assert len(inbox_a) == 1
    assert inbox_a[0].topic == "topic-A"
    assert inbox_a[0].payload == "Msg for A"
    
    # Check Inbox B
    assert len(inbox_b) == 1
    assert inbox_b[0].topic == "topic-B"
    assert inbox_b[0].payload == "Msg for B"
    
    await bus.stop()

@pytest.mark.asyncio
async def test_concurrency_integrity():
    """Verify no messages are lost when multiple producers spam a single topic."""
    bus = MessageBus()
    await bus.start()
    
    collected_ids = set()
    expected_count = 100
    
    async def collector(msg):
        collected_ids.add(msg.payload)
        
    bus.subscribe("high-traffic", collector)
    
    # Define producer
    async def produce(start_id, count):
        for i in range(count):
            await bus.publish("high-traffic", "spammer", start_id + i)
            # No sleep, max pressure
            
    # Run 4 concurrent producers, each sending 25 messages
    await asyncio.gather(
        produce(0, 25),
        produce(25, 25),
        produce(50, 25),
        produce(75, 25)
    )
    
    # Allow processing time
    await asyncio.sleep(0.2)
    
    assert len(collected_ids) == expected_count, f"Expected {expected_count} unique messages, got {len(collected_ids)}"
    
    # Verify strict range check
    assert min(collected_ids) == 0
    assert max(collected_ids) == 99
    
    await bus.stop()
