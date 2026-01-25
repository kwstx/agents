
from agents.base_agent import BaseAgent
import asyncio

class InfiniteLoopAgent(BaseAgent):
    async def process_task(self, task):
        while True:
            await asyncio.sleep(0.1)
