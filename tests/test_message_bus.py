import pytest
import asyncio
from utils.message_bus import MessageBus

@pytest.mark.asyncio
async def test_message_bus_subscription():
    bus = MessageBus()
    await bus.start()
    
    received_messages = []
    
    async def handler(message):
        received_messages.append(message)
        
    bus.subscribe("test_topic", handler)
    
    await bus.publish("test_topic", "sender", "payload")
    
    # Wait briefly for processing
    await asyncio.sleep(0.1)
    
    assert len(received_messages) == 1
    assert received_messages[0].topic == "test_topic"
    assert received_messages[0].payload == "payload"
    assert received_messages[0].sender == "sender"

    await bus.stop()

@pytest.mark.asyncio
async def test_message_bus_multiple_subscribers():
    bus = MessageBus()
    await bus.start()
    
    count_1 = 0
    count_2 = 0
    
    async def handler_1(message):
        nonlocal count_1
        count_1 += 1
        
    def handler_2(message):
        nonlocal count_2
        count_2 += 1
        
    bus.subscribe("topic_A", handler_1)
    bus.subscribe("topic_A", handler_2)
    
    await bus.publish("topic_A", "sender", "data")
    await asyncio.sleep(0.1)
    
    assert count_1 == 1
    assert count_2 == 1
    
    await bus.stop()
