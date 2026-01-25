import pytest
import asyncio
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

class RecordingAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.received_messages = []

    async def process_task(self, task):
        pass

    async def receive_message(self, message: Message):
        """Override to capture messages."""
        # Simple filter: only accept if addressed to me or all, or subscribed topic
        if message.receiver and message.receiver not in [self.agent_id, "all"]:
            return 
            
        self.received_messages.append(message)
        await super().receive_message(message)

# Monkey patch BaseAgent.receive_message mechanism for the test context
# Since the default BaseAgent.receive_message is just a handler, 
# we need to ensure the subscription actually calls this instance method.
# In the test setup, we will explicitly bind the handler.

@pytest.mark.asyncio
async def test_deterministic_delivery_ideal_conditions():
    """
    Verify that in ideal conditions (no latency, no failure):
    1. All messages are delivered.
    2. Order is preserved exactly (FIFO).
    3. Messages are delivered to the correct recipient.
    """
    bus = MessageBus(log_path="logs/test_determinism.jsonl")
    await bus.start()

    sender = RecordingAgent("sender_agent", bus)
    receiver = RecordingAgent("receiver_agent", bus)
    
    await sender.start()
    await receiver.start()

    # Manual Subscription for the test
    # In a real scenario, agents might subscribe to their own ID or specific topics.
    # Here we subscribe the receiver to "data_stream".
    bus.subscribe("data_stream", receiver.receive_message)

    MESSAGE_COUNT = 100
    
    # 1. Send Sequence of Messages
    print(f"Sending {MESSAGE_COUNT} messages...")
    for i in range(MESSAGE_COUNT):
        payload = {"seq": i, "content": f"msg_{i}"}
        await sender.send_message(
            topic="data_stream", 
            payload=payload, 
            message_type="event", 
            receiver="receiver_agent"
        )
    
    # 2. Wait for Processing
    # Since queue is FIFO and local, this should be fast. 
    # We give a small buffer to ensure consumer task runs.
    await asyncio.sleep(0.5)
    
    # 3. Verify Assertions
    received = receiver.received_messages
    
    # Assertion A: Completeness
    assert len(received) == MESSAGE_COUNT, \
        f"Expected {MESSAGE_COUNT} messages, got {len(received)}"
        
    # Assertion B: Order & Integrity
    for i, msg in enumerate(received):
        assert msg.sender == "sender_agent"
        assert msg.receiver == "receiver_agent"
        assert msg.payload["seq"] == i, \
             f"Message out of order! Expected seq {i}, got {msg.payload['seq']}"
        assert msg.trace_id is not None
        
    print("Verification Passed: 100/100 messages received in perfect order.")

    await sender.stop()
    await receiver.stop()
    await bus.stop()
