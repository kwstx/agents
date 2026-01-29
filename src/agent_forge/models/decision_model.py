import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass

@dataclass
class ModelConfig:
    input_size: int = 4  # Agent X, Agent Y, Goal X, Goal Y
    hidden_size: int = 64
    output_size: int = 4 # UP, DOWN, LEFT, RIGHT
    learning_rate: float = 0.001

class GridDecisionModel(nn.Module):
    def __init__(self, config: ModelConfig = ModelConfig()):
        super(GridDecisionModel, self).__init__()
        self.fc1 = nn.Linear(config.input_size, config.hidden_size)
        self.fc2 = nn.Linear(config.hidden_size, config.hidden_size)
        self.fc3 = nn.Linear(config.hidden_size, config.output_size)
        
    def forward(self, x):
        if torch.isnan(x).any():
            raise ValueError("Input contains NaNs")
            
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x
