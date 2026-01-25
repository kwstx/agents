from agents.base_agent import BaseAgent
import logging

class DummyAgent(BaseAgent):
    """
    Dummy agent that tracks its own lifecycle events.
    """
    # Class-level tracker for verification
    event_log = []

    def __init__(self, agent_id: str, message_bus=None):
        super().__init__(agent_id, message_bus)
        DummyAgent.event_log.append(f"init_{agent_id}")

    async def setup(self):
        DummyAgent.event_log.append(f"setup_{self.agent_id}")

    async def process_task(self, task):
        DummyAgent.event_log.append(f"process_{self.agent_id}")
        return "processed"
    
    @classmethod
    def reset_log(cls):
        cls.event_log = []
