import torch
import torch.nn as nn
import torch.optim as optim
import random
import os
import numpy as np
from collections import deque
from .decision_model import GridDecisionModel, ModelConfig

class DQNTrainer:
    def __init__(self, model: GridDecisionModel, config: ModelConfig = ModelConfig()):
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)
        self.criterion = nn.MSELoss()
        self.memory = deque(maxlen=10000)
        self.batch_size = 64
        self.gamma = 0.99  # Discount factor
        
    def store_experience(self, state, action, reward, next_state, done):
        """Stores a transition in the replay buffer.
           State/Next_state should be lists or numpy arrays."""
        self.memory.append((state, action, reward, next_state, done))
        
    def train_step(self):
        if len(self.memory) < self.batch_size:
            return 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        
        # Unzip batch
        states, actions, rewards, next_states, dones = zip(*batch)
        
        # Convert to tensors
        states_tensor = torch.FloatTensor(np.array(states))
        actions_tensor = torch.LongTensor(actions).unsqueeze(1)
        rewards_tensor = torch.FloatTensor(rewards).unsqueeze(1)
        next_states_tensor = torch.FloatTensor(np.array(next_states))
        dones_tensor = torch.FloatTensor(dones).unsqueeze(1)
        
        # Q(s, a)
        q_values = self.model(states_tensor)
        current_q = q_values.gather(1, actions_tensor)
        
        # target = r + gamma * max(Q(s', a'))
        with torch.no_grad():
            next_q_values = self.model(next_states_tensor)
            max_next_q = next_q_values.max(1)[0].unsqueeze(1)
            target_q = rewards_tensor + (self.gamma * max_next_q * (1 - dones_tensor))
            
        loss = self.criterion(current_q, target_q)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
        
    def save_model(self, path="models/grid_mlp.pth"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.model.state_dict(), path)
        
    def load_model(self, path="models/grid_mlp.pth"):
        if os.path.exists(path):
            self.model.load_state_dict(torch.load(path))
            self.model.eval()
            return True
        return False
