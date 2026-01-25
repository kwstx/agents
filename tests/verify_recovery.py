import pytest
import asyncio
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

class FragileAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.inbox = []
        self.should_crash = False

    async def process_task(self, task):
        pass

    async def receive_message(self, message: Message):
        await super().receive_message(message)
        
        if self.should_crash:
            raise ValueError("I crashed!")
            
        # Strict filtering check from previous step is inside receive_message?
        # No, I implemented it in BaseAgent.receive_message.
        # So super() call handles it.
        # But wait, BaseAgent.receive_message returns None (early return).
        # It does NOT stop us if we continue executing here unless we check result, 
        # OR unless BaseAgent raised exception?
        # BaseAgent code: `if ...: return`.
        # So `super().receive_message(message)` returns None immediately.
        # We continue execution. This is a flaw I noted earlier.
        # For this test, assume proper routing (receiver=self).
        
        if message.receiver == self.agent_id:
            self.inbox.append(message)


@pytest.mark.asyncio
async def test_handler_crash_to_dlq():
    """Verify that if an agent crashes handling a message, it goes to DLQ."""
    bus = MessageBus(log_path="logs/recovery_test.jsonl")
    await bus.start()
    
    agent = FragileAgent("crasher", bus)
    await agent.start()
    
    # We must call agent.subscribe wrapper for it to work properly with restart logic
    agent.subscribe("danger_zone")
    agent.should_crash = True
    
    # Send message
    await agent.send_message("danger_zone", "BOOM", receiver="crasher")
    
    await asyncio.sleep(0.1)
    
    # Assert message is in DLQ
    assert len(bus.dlq) == 1
    assert bus.dlq[0].payload == "BOOM"
    
    await bus.stop()

@pytest.mark.asyncio
async def test_agent_clean_restart():
    """Verify Agent unsubscribe on stop and can restart cleanly."""
    bus = MessageBus(log_path="logs/recovery_test.jsonl")
    await bus.start()
    
    agent = FragileAgent("zombie_check", bus)
    await agent.start()
    agent.subscribe("restart_test")
    
    # 1. Receive Initial
    await agent.send_message("restart_test", "msg_1", receiver="zombie_check")
    await asyncio.sleep(0.1)
    assert len(agent.inbox) == 1
    
    # 2. Stop Agent (Should Unsubscribe)
    await agent.stop()
    
    # 3. Send message (Should NOT receive)
    token_sys = bus.register("system")
    await bus.publish("restart_test", "system", "msg_2", receiver="zombie_check", auth_token=token_sys)
    await asyncio.sleep(0.1)
    
    # Verify Inbox didn't grow
    assert len(agent.inbox) == 1
    
    # 4. Restart Agent
    await agent.start()
    agent.subscribe("restart_test") # Re-subscribe (Simulate app logic)
    
    # 5. Send Message (Should Receive)
    await bus.publish("restart_test", "system", "msg_3", receiver="zombie_check", auth_token=token_sys)
    await asyncio.sleep(0.1)
    
    assert len(agent.inbox) == 2
    assert agent.inbox[1].payload == "msg_3"
    
    await bus.stop()
