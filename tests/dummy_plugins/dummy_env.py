from environments.base_env import BaseEnvironment
from typing import Any, Tuple, Dict

class DummyEnv(BaseEnvironment):
    """
    Dummy environment that tracks its own lifecycle events.
    """
    # Class-level tracker for verification
    event_log = []

    def __init__(self):
        DummyEnv.event_log.append("init_env")

    def reset(self) -> Any:
        DummyEnv.event_log.append("reset_env")
        return "reset_state"

    def step(self, action: Any) -> Tuple[Any, float, bool, Dict[str, Any]]:
        DummyEnv.event_log.append("step_env")
        return "new_state", 1.0, False, {}

    @classmethod
    def reset_log(cls):
        cls.event_log = []
