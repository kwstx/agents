import pytest
import asyncio
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

class PubSubAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.inbox = []
    
    async def process_task(self, task):
        pass

    async def receive_message(self, message: Message):
        # We simulate the default filter behavior in a clean way
        # But for this test, we want to know what the bus *delivered*, 
        # regardless of whether the agent "wants" it or not.
        # So we append everything delivered to us.
        self.inbox.append(message)
        await super().receive_message(message)

# Helper to bind method
def get_handler(agent):
    return agent.receive_message

@pytest.mark.asyncio
async def test_pubsub_broadcast():
    """Verify all subscribers receive the message."""
    bus = MessageBus(log_path="logs/pubsub_test.jsonl")
    await bus.start()
    
    agents = [PubSubAgent(f"sub_{i}", bus) for i in range(3)]
    for a in agents:
        bus.subscribe("broadcast_channel", get_handler(a))
        
    await bus.publish("broadcast_channel", "publisher", "hello everyone", message_type="event")
    await asyncio.sleep(0.1)
    
    for a in agents:
        assert len(a.inbox) == 1
        assert a.inbox[0].payload == "hello everyone"
        
    await bus.stop()

@pytest.mark.asyncio
async def test_late_subscriber_interaction():
    """Verify late subscribers do not receive past messages but do receive future ones."""
    bus = MessageBus(log_path="logs/pubsub_test.jsonl")
    await bus.start()
    
    early_bird = PubSubAgent("early", bus)
    late_comer = PubSubAgent("late", bus)
    
    bus.subscribe("news", get_handler(early_bird))
    
    # 1. Early message
    await bus.publish("news", "pub", "morning news")
    await asyncio.sleep(0.1)
    
    # 2. Late subscription
    bus.subscribe("news", get_handler(late_comer))
    
    # 3. Late message
    await bus.publish("news", "pub", "evening news")
    await asyncio.sleep(0.1)
    
    assert len(early_bird.inbox) == 2
    assert len(late_comer.inbox) == 1
    assert late_comer.inbox[0].payload == "evening news"
    
    await bus.stop()

@pytest.mark.asyncio
async def test_unsubscribe_semantics():
    """Verify unsubscribed agents stop receiving messages."""
    bus = MessageBus(log_path="logs/pubsub_test.jsonl")
    await bus.start()
    
    sub = PubSubAgent("leaver", bus)
    handler = get_handler(sub)
    bus.subscribe("channel_x", handler)
    
    # Received
    await bus.publish("channel_x", "pub", "msg_1")
    await asyncio.sleep(0.1)
    assert len(sub.inbox) == 1
    
    # Unsubscribe
    bus.unsubscribe("channel_x", handler)
    
    # Not Received
    await bus.publish("channel_x", "pub", "msg_2")
    await asyncio.sleep(0.1)
    assert len(sub.inbox) == 1 # Count should not increase
    
    await bus.stop()

@pytest.mark.asyncio
async def test_private_message_leakage_on_shared_topic():
    """
    Verify that if a message is sent to a specific receiver on a SHARED topic,
    it is technically delivered to all subscribers of that topic by the bus,
    BUT intended recipients can distinguish it.
    
    *Strictly speaking, a true private message should probably not use a shared topic
    if privacy is paramount, or encryption should be used.
    For this Pub/Sub test, we verify the delivery mechanics: IT WILL BE DELIVERED.*
    """
    bus = MessageBus(log_path="logs/pubsub_test.jsonl")
    await bus.start()
    
    alice = PubSubAgent("alice", bus)
    bob = PubSubAgent("bob", bus) # Eavesdropper logic test
    
    bus.subscribe("chat", get_handler(alice))
    bus.subscribe("chat", get_handler(bob))
    
    # Send to Alice only, but on shared topic
    await bus.publish("chat", "sender", "secret for alice", receiver="alice")
    await asyncio.sleep(0.1)
    
    # Both received it physically from the bus perspective
    assert len(alice.inbox) == 1
    assert len(bob.inbox) == 1
    
    # But checking the content, Bob can see it's for Alice
    assert bob.inbox[0].receiver == "alice"
    
    # This confirms the Bus broadcasts to TOPIC, not filtered by RECEIVER at the Bus level.
    # This is the expected behavior for a Topic-based Pub/Sub.
    
    await bus.stop()
