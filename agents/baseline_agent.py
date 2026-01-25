import random
import asyncio
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from environments.simulation_engine import SimulationEngine

class RandomBaselineAgent(BaseAgent):
    """
    Naive baseline agent that moves randomly.
    Used to establish a performance floor.
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, engine: SimulationEngine):
        super().__init__(agent_id, message_bus)
        self.engine = engine
        self.running = False

    async def process_task(self, task):
        if task == "start_logistics":
            asyncio.create_task(self.run_loop())
            return "Random Loop Started"
        return f"Unknown task: {task}"

    async def run_loop(self):
        self.running = True
        while self.running:
            # Random Walk
            action = random.choice(["UP", "DOWN", "LEFT", "RIGHT", "STAY", "PICKUP", "DROPOFF", "CHARGE"])
            await self.engine.perform_action(self.agent_id, action)
            
            # Interact blindly
            if random.random() < 0.1:
                await self.engine.perform_action(self.agent_id, "PICKUP")
            if random.random() < 0.1:
                await self.engine.perform_action(self.agent_id, "DROPOFF")
                
            await asyncio.sleep(0.1)

    async def stop(self):
        self.running = False
