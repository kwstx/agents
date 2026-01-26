import asyncio
from typing import List, Any
from agent_forge.core.base_agent import BaseAgent
from agent_forge.core.engine import SimulationEngine
from agent_forge.utils.message_bus import MessageBus

class ReplayStubAgent(BaseAgent):
    """
    Agent that blindly replays a sequence of actions.
    Used to verify Environment Determinism.
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, engine: SimulationEngine, action_trace: List[str]):
        super().__init__(agent_id, message_bus)
        self.engine = engine
        self.action_trace = action_trace # List of actions
        self.step_idx = 0
        self.enable_checkpoints = False

    async def start(self):
        self.running = True
        # No loop, controlled externally or via step()

    async def step(self):
        if self.step_idx < len(self.action_trace):
            action = self.action_trace[self.step_idx]
            self.step_idx += 1
            
            # Execute
            await self.engine.perform_action(self.agent_id, action)
        else:
            # idle
            pass
