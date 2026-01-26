from abc import ABC, abstractmethod
from typing import Any, Tuple, Dict, Optional

class BaseEnvironment(ABC):
    """Abstract base class for all simulation environments."""

    @abstractmethod
    def reset(self) -> Any:
        """
        Resets the environment to an initial state.
        Returns:
            The initial observation/state.
        """
        pass

    @abstractmethod
    def step(self, action: Any) -> Tuple[Any, float, bool, Dict[str, Any]]:
        """
        Executes one time step within the environment.
        Args:
            action: The action to perform.
        Returns:
            A tuple containing:
            - observation (Any): The new state/observation.
            - reward (float): The reward received.
            - done (bool): Whether the episode has terminated.
            - info (Dict): Diagnostic information.
        """
        pass

    def render(self):
        """Optional method to visualize the environment."""
        pass
