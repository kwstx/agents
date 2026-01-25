from agents.base_agent import BaseAgent

class AgentV1Legacy(BaseAgent):
    """
    Legacy agent that uses 'perform' instead of 'process_task'.
    """
    async def perform(self, task):
        return f"v1_legacy_result: {task}"
