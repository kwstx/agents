import random
from typing import Tuple, Dict, Any
from environments.grid_world import GridWorld

class NoisyGridWorld(GridWorld):
    """
    A GridWorld with slippery floors and sensor noise.
    """
    def __init__(self, size: int = 5, slippery_prob: float = 0.2):
        super().__init__(size)
        self.slippery_prob = slippery_prob
        
    def step(self, action: str) -> Tuple[Tuple[int, int], float, bool, Dict[str, Any]]:
        # Stochastic Transition: Slippery Floor
        # If slippery, action is replaced by a random neighbor action
        effective_action = action
        
        if random.random() < self.slippery_prob:
            possible_slips = ["UP", "DOWN", "LEFT", "RIGHT"]
            effective_action = random.choice(possible_slips)
            
        # Delegate to parent
        state, reward, done, info = super().step(effective_action)
        
        # Add noise metadata to info
        info["effective_action"] = effective_action
        info["slippage"] = (effective_action != action)
        
        return state, reward, done, info
