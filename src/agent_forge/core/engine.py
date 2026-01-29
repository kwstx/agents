import time
import random
import asyncio
import inspect
from typing import Any, Dict, Optional
from agent_forge.core.base_env import BaseEnvironment
from agent_forge.utils.interaction_logger import InteractionLogger
from agent_forge.core.adversarial import AdversarialMiddleware, AdversarialConfig
from agent_forge.core.compliance import ComplianceAuditor

class SimulationEngine:
    def __init__(self, 
                 env: Optional[BaseEnvironment] = None, 
                 logger: Optional[InteractionLogger] = None,
                 stress_config: Optional[Dict[str, Any]] = None):
        """
        ...
        """
        self.env = env
        self.logger = logger
        self.stress_config = stress_config or {}
        self.on_step_callback = None # Callable[[Dict], Awaitable[None]]
        
        # Auditor
        # Grid size hardcoded for MVP or inferred? 
        # Ideally passed in config, defaulting to 10 for now matching Warehouse default
        self.auditor = ComplianceAuditor(grid_size=10)
        
        # Seed Control
        if stress_config and "seed" in stress_config:
            self.seed = stress_config["seed"]
            random.seed(self.seed)
            if self.logger:
                self.logger.log_interaction("engine", "seeded", self.seed, 0.0, {"seed": self.seed}, "")
        
        
        # Adversarial Middleware
        # For now, disable by default unless stress_config says otherwise
        adv_conf = AdversarialConfig(
            enabled=True if stress_config else False,
            jitter_rate=stress_config.get("latency_rate", 0.0) if stress_config else 0.0,
            latency_range=stress_config.get("latency_range", (0.0, 0.0)) if stress_config else (0.0, 0.0),
            drop_rate=stress_config.get("failure_rate", 0.0) if stress_config else 0.0,
        )
        self.adversary = AdversarialMiddleware(adv_conf)
        
        # State cache for agents
        self._current_observation = None
        self._last_reward = 0.0
        self._last_done = False
        self._last_info = {}
        
        # Initialize
        self._sequence_id = 0
        self._pause_event = asyncio.Event()
        self._pause_event.set() # Start unpaused
        self.reset()

    def set_env(self, env: BaseEnvironment):
        """Swaps the environment and resets the state."""
        self.env = env
        self.reset()
        
    def pause(self):
        """Pauses the simulation."""
        self._pause_event.clear()
        
    def resume(self):
        """Resumes the simulation."""
        self._pause_event.set()

    def reset(self):
        if self.env:
            self._current_observation = self.env.reset()
        else:
            self._current_observation = None
            
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
        await self._pause_event.wait()
        await self._apply_stress()
        if hasattr(self.env, "get_agent_state"):
            return self.env.get_agent_state(agent_id)
        return self._current_observation

    async def perform_action(self, agent_id: str, action: Any) -> bool:
        """
        Executes an action in the environment.
        Returns True if successful, False if the episode is done or failed.
        """
        # await self._apply_stress() # Legacy simple stress
        
        # New Adversarial Middleware
        should_proceed = await self.adversary.intercept_action(agent_id, str(action))
        if not should_proceed:
             # Action Dropped
             return True # Return True (alive) but did nothing
        
        # Check Pause
        await self._pause_event.wait()
        
        if self._last_done:
            return False

        # Execute step
        start = time.time()
        # Execute step
        start = time.time()
        try:
             obs, reward, done, info = self.env.step(action, agent_id=agent_id)
        except TypeError:
             obs, reward, done, info = self.env.step(action)
        duration = time.time() - start
        info["duration"] = duration
        
        # Audit Check
        violations = self.auditor.audit_state(agent_id, obs)
        if violations:
            # Convert Violation objects to dicts for JSON serialization
            info["violations"] = [
                {"rule": v.rule_id, "msg": v.message, "context": v.context} 
                for v in violations
            ]
        
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

        if self.on_step_callback:
            # Broadcast the full state delta or snapshot
            # For MVP, we send the agent's observation update
            # Ideally we send the Full Env State if possible
            self._sequence_id += 1
            update = {
                "type": "step",
                "seq_id": self._sequence_id,
                "agent_id": agent_id,
                "observation": obs,
                "info": info,
                "timestamp": time.time()
            }
            if inspect.iscoroutinefunction(self.on_step_callback):
                await self.on_step_callback(update)
            else:
                self.on_step_callback(update)
            
        return not done

    async def get_feedback(self, agent_id: str) -> Dict[str, Any]:
        """Returns the feedback (reward, done, info) from the last action."""
        await self._apply_stress()
        return {
            "reward": self._last_reward,
            "done": self._last_done,
            "info": self._last_info
        }
