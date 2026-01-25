import pytest
import asyncio
import time
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

class PingAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.pong_received = asyncio.Event()
        self.pong_msg = None

    async def process_task(self, task):
        pass

    async def receive_message(self, message: Message):
        if message.payload == "PONG":
            self.pong_msg = message
            self.pong_received.set()
        await super().receive_message(message)

# Helper to drain queue between tests
async def drain_queue(bus):
    while bus.qsize > 0:
        await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_latency_injection():
    """Verify that latency settings delay message delivery."""
    bus = MessageBus(log_path="logs/fault_test.jsonl")
    # Set Latency: 0.1s to 0.2s
    bus.set_chaos(latency_min=0.1, latency_max=0.2, drop_rate=0)
    await bus.start()
    
    receiver = PingAgent("receiver", bus)
    bus.subscribe("ping", receiver.receive_message)
    
    start_time = time.time()
    await bus.publish("ping", "sender", "PONG", message_type="event")
    
    try:
        await asyncio.wait_for(receiver.pong_received.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pass
        
    end_time = time.time()
    duration = end_time - start_time
    
    # Expectation: Duration >= 0.1s (latency)
    print(f"Latency Test Duration: {duration:.4f}s")
    assert duration >= 0.1, f"Message was too fast! duration={duration}"
    assert receiver.pong_received.is_set()
    
    await bus.stop()

@pytest.mark.asyncio
async def test_packet_drop_injection():
    """Verify roughly 50% drop rate."""
    bus = MessageBus(log_path="logs/fault_test.jsonl")
    # Set Drop Rate: 50%
    bus.set_chaos(latency_min=0.0, latency_max=0.0, drop_rate=0.5)
    await bus.start()
    
    received_count = 0
    
    async def counter(msg):
        nonlocal received_count
        received_count += 1
        
    bus.subscribe("drop_test", counter)
    
    Total = 100
    for i in range(Total):
        await bus.publish("drop_test", "sender", f"msg_{i}", message_type="event")
        
    await asyncio.sleep(0.5) # Wait for processing
    
    print(f"Drop Test: Sent {Total}, Received {received_count}")
    
    # Probabilistic check: Should be roughly 50. Let's say between 30 and 70.
    assert 30 <= received_count <= 70, f"Drop rate anomaly! Received {received_count}/{Total}"
    # Ensure it's not perfect (unlikely to be exactly 100 if drop is on)
    assert received_count < Total, "Nothing was dropped!"
    
    await bus.stop()

@pytest.mark.asyncio
async def test_robust_agent_timeout():
    """Verify an agent can handle missing response (timeout)."""
    bus = MessageBus(log_path="logs/fault_test.jsonl")
    # 100% Drop Rate -> Guaranteed Timeout
    bus.set_chaos(drop_rate=1.0)
    await bus.start()
    
    receiver = PingAgent("receiver", bus)
    bus.subscribe("ping", receiver.receive_message)
    
    # Act: Wait for PONG that will never come
    await bus.publish("ping", "sender", "PONG", message_type="event")
    
    with pytest.raises(asyncio.TimeoutError):
        # Agent logic usually involves wait_for
        await asyncio.wait_for(receiver.pong_received.wait(), timeout=0.2)
        
    await bus.stop()
