
from agents.base_agent import BaseAgent
import os

class HackerAgent(BaseAgent):
    async def process_task(self, task):
        return os.getcwd()
