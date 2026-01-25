
from agents.base_agent import BaseAgent
import subprocess

class SubprocessAgent(BaseAgent):
    async def process_task(self, task):
        return "owned"
