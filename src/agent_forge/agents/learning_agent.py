import torch
import numpy as np
import random
import asyncio
from typing import List, Any
from agent_forge.agents.grid_agent import GridAgent
from agent_forge.models.decision_model import GridDecisionModel, ModelConfig
from agent_forge.models.trainer import DQNTrainer
from agent_forge.utils.message_bus import MessageBus
from agent_forge.environments.grid_world import GridWorld

class LearningGridAgent(GridAgent):
    def __init__(self, agent_id: str, message_bus: MessageBus, env: GridWorld, model: GridDecisionModel = None, hooks: list = None):
        super().__init__(agent_id, message_bus, env)
        
        # Initialize Model and Trainer
        if model is None:
            model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
            
        self.model = model
        self.trainer = DQNTrainer(self.model)
        self.hooks = hooks or []
        
        # Hyperparameters
        self.epsilon = 1.0  # Exploration rate
        
        # Persistence: Try Load
        model_path = f"models/{self.agent_id}_mlp.pth"
        if self.trainer.load_model(model_path):
            self.epsilon = 0.1 # Lower exploration if pre-trained
            self.logger.info(f"Loaded existing model from {model_path}")
        else:
            self.logger.info(f"Initialized new model. No checkpoint at {model_path}")

        self.epsilon_min = 0.1
        self.epsilon_decay = 0.995
        self.training_enabled = True

    def _get_state_vector(self, position, goal):
        """Normalizes state to [0,1] range for the model."""
        size = float(self.env.size) if self.env.size > 0 else 1.0
        return [
            position[0] / size, 
            position[1] / size, 
            goal[0] / size, 
            goal[1] / size
        ]

    async def process_task(self, task: Any):
        """
        Handles tasks. Overridden to intercept specific commands if needed, 
        otherwise defaults to parent behavior.
        """
        if task == "navigate_with_learning":
            return await self._navigate_to_goal()
        return await super().process_task(task)

    async def _navigate_to_goal(self):
        """
        Overridden navigation using model + hooks.
        """
        obs = self.env.reset(agent_id=self.agent_id)
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
            
            # Select Action
            action_idx = self.select_action(state_vector)
            actions = ["UP", "DOWN", "LEFT", "RIGHT"]
            action = actions[action_idx]

            # Execute action
            next_obs, reward, done, info = self.env.step(action, agent_id=self.agent_id)
            next_state_vector = self._get_state_vector(next_obs, self.env.goal)

            # Hook: on_step_end (allow modifying reward)
            for hook in self.hooks:
                if hasattr(hook, 'on_step_end'):
                    result = hook.on_step_end(self, state_vector, action_idx, reward, next_state_vector, done)
                    if result is not None:
                        reward = result
            
            # Learn
            self.learn_from_step(state_vector, action_idx, reward, next_state_vector, done)

            # Update state
            self.state["current_position"] = next_obs
            self.state["total_reward"] += reward
            
            # Logging
            step_summary = f"Step {steps}: Action={action} ({action_idx}), Pos={next_obs}, Reward={reward:.2f}, Epsilon={self.epsilon:.2f}"
            self.logger.info(step_summary)
            transcript.append(step_summary)
            
            steps += 1
            
            # Allow async context switching
            await asyncio.sleep(0)
            
        # End of Episode
        self.on_episode_end()

        return transcript

    def learn_from_step(self, state_vector, action_idx, reward, next_state_vector, done):
        """External facing learning step."""
        if self.training_enabled:
            self.trainer.store_experience(state_vector, action_idx, reward, next_state_vector, done)
            loss = self.trainer.train_step()
            # We could log loss here if we had step count context, but logger works.
            # self.logger.info(f"Loss: {loss}")

    def on_episode_end(self):
        """External facing episode completion handler."""
        if self.training_enabled:
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
            # Checkpoint occasionally
            if random.random() < 0.1: # 10% chance to save per episode to avoid IO spam
                self.trainer.save_model(f"models/{self.agent_id}_mlp.pth")

    def select_action(self, state_vector):
        """Selects an action based on epsilon-greedy policy."""
        if self.training_enabled and random.random() < self.epsilon:
            return random.randint(0, 3)
        else:
            state_tensor = torch.FloatTensor([state_vector])
            with torch.no_grad():
                q_values = self.model(state_tensor)
                return torch.argmax(q_values).item()
