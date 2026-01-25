from agents.base_agent import BaseAgent
from environments.base_env import BaseEnvironment

class AgentMissingMethod(BaseAgent):
    """
    Intentionally malformed agent missing 'process_task'.
    """
    pass

class EnvMissingReset(BaseEnvironment):
    """
    Intentionally malformed environment missing 'reset'.
    """
    def step(self, action):
        pass

class EnvMissingStep(BaseEnvironment):
    """
    Intentionally malformed environment missing 'step'.
    """
    def reset(self):
        pass
