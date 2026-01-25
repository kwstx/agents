import torch
import numpy as np
import random
from agents.grid_agent import GridAgent
from models.decision_model import GridDecisionModel
from models.trainer import DQNTrainer
from utils.message_bus import MessageBus
from environments.grid_world import GridWorld

class LearningGridAgent(GridAgent):
    def __init__(self, agent_id: str, message_bus: MessageBus, env: GridWorld, model: GridDecisionModel, hooks: list = None):
        super().__init__(agent_id, message_bus, env)
        self.model = model
        self.hooks = hooks or []
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.995
        
    def _get_state_vector(self, position, goal):
        """Normalizes state to [0,1] range for the model."""
        size = float(self.env.size)
        return [
            position[0] / size, 
            position[1] / size, 
            goal[0] / size, 
            goal[1] / size
        ]

    async def _navigate_to_goal(self):
        """
        Overridden navigation using model + hooks.
        """
        obs = self.env.reset()
        self.state["current_position"] = obs
        self.state["total_reward"] = 0.0
        
        done = False
        steps = 0
        transcript = []
        max_steps = 50 
        
        target_x, target_y = self.env.goal
        
        while not done and steps < max_steps:
            current_x, current_y = self.state["current_position"]
            state_vector = self._get_state_vector((current_x, current_y), self.env.goal)
            
            action_idx = self.select_action(state_vector)
            
            actions = ["UP", "DOWN", "LEFT", "RIGHT"]
            action = actions[action_idx]

    def select_action(self, state_vector):
        """Selects an action based on epsilon-greedy policy."""
        if random.random() < self.epsilon:
            return random.randint(0, 3)
        else:
            state_tensor = torch.FloatTensor([state_vector])
            with torch.no_grad():
                q_values = self.model(state_tensor)
                return torch.argmax(q_values).item()
            
            # Execute action
            next_obs, reward, done, info = self.env.step(action)
            
            # Hook: on_step_end
            next_state_vector = self._get_state_vector(next_obs, self.env.goal)
            for hook in self.hooks:
                result = hook.on_step_end(self, state_vector, action_idx, reward, next_state_vector, done)
                if result is not None:
                    reward = result
            
            # Update state
            self.state["current_position"] = next_obs
            self.state["total_reward"] += reward
            
            # Logging
            step_summary = f"Step {steps}: Action={action} ({action_idx}), Pos={next_obs}, Reward={reward}, Epsilon={self.epsilon:.2f}"
            transcript.append(step_summary)
            
            steps += 1
            
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        return transcript
