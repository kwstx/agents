import time
import random
import asyncio
from typing import Any, Dict, Optional
from environments.base_env import BaseEnvironment
from utils.interaction_logger import InteractionLogger

class SimulationEngine:
    def __init__(self, 
                 env: BaseEnvironment, 
                 logger: Optional[InteractionLogger] = None,
                 stress_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            env: The underlying environment to simulate.
            logger: Optional logger for persisting interactions.
            stress_config: Configuration for stress testing (latency, failures).
                           e.g., {"latency_range": (0.1, 0.5), "failure_rate": 0.1}
        """
        self.env = env
        self.logger = logger
        self.stress_config = stress_config or {}
        
        # State cache for agents
        self._current_observation = None
        self._last_reward = 0.0
        self._last_done = False
        self._last_info = {}
        
        # Initialize
        self.reset()

    def reset(self):
        self._current_observation = self.env.reset()
        self._last_reward = 0.0
        self._last_done = False
        self._last_info = {}
        return self._current_observation

    async def _apply_stress(self):
        """Applies artificial latency or failures based on config."""
        # Latency
        if "latency_range" in self.stress_config:
            min_delay, max_delay = self.stress_config["latency_range"]
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)
            
        # Failure
        if "failure_rate" in self.stress_config:
            if random.random() < self.stress_config["failure_rate"]:
                raise Exception("Simulated Network Failure")

    async def get_state(self, agent_id: str) -> Any:
        """Returns the current perception of the state for the agent."""
        await self._apply_stress()
        return self._current_observation

    async def perform_action(self, agent_id: str, action: Any) -> bool:
        """
        Executes an action in the environment.
        Returns True if successful, False if the episode is done or failed.
        """
        await self._apply_stress()
        
        if self._last_done:
            return False

        # Execute step
        start = time.time()
        obs, reward, done, info = self.env.step(action)
        duration = time.time() - start
        info["duration"] = duration
        
        # Update internal state
        self._current_observation = obs
        self._last_reward = reward
        self._last_done = done
        self._last_info = info
        
        # Log interaction
        if self.logger:
            # Deterministic hash of state
            state_str = str(obs) 
            state_hash = str(hash(state_str)) # Simple hash for MVP tuple state
            
            self.logger.log_interaction(
                agent_id=agent_id,
                action=str(action),
                state=obs,
                reward=reward,
                metadata=info,
                state_hash=state_hash
            )
            
        return not done

    async def get_feedback(self, agent_id: str) -> Dict[str, Any]:
        """Returns the feedback (reward, done, info) from the last action."""
        await self._apply_stress()
        return {
            "reward": self._last_reward,
            "done": self._last_done,
            "info": self._last_info
        }
