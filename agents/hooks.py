from typing import Any, Dict
from models.trainer import DQNTrainer

class AgentHook:
    """Base class for agent hooks that intercept lifecycle events."""
    def on_step_end(self, agent, state_vector, action_idx, reward, next_state_vector, done):
        """
        Called after environment step.
        Return a float to modify the reward for subsequent hooks/agent state.
        Return None to keep reward unchanged.
        """
        return None

class DQNTrainHook(AgentHook):
    """Hook that triggers generic DQN training steps."""
    def __init__(self, trainer: DQNTrainer):
        self.trainer = trainer

    def on_step_end(self, agent, state_vector, action_idx, reward, next_state_vector, done):
        """Standard training hook."""
        # Store experience
        self.trainer.store_experience(state_vector, action_idx, reward, next_state_vector, done)
        
        # Train model
        loss = self.trainer.train_step()
        
        # Optionally log loss if the agent has a logger, or store it in agent state for visibility
        # for simplicity, we do nothing extra here, effectively "auto-refining" in background
