from agents.base_agent import BaseAgent

class AgentV2Modern(BaseAgent):
    """
    Modern agent that uses 'process_task'.
    """
    async def process_task(self, task):
        return f"v2_modern_result: {task}"
