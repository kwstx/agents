from typing import Any, Tuple, Dict
from environments.base_env import BaseEnvironment

class GridWorld(BaseEnvironment):
    """
    A simple 5x5 Grid World.
    State: (x, y) tuple.
    Goal: Reach (4, 4).
    Actions: "UP", "DOWN", "LEFT", "RIGHT".
    """
    
    def __init__(self, size: int = 5):
        self.size = size
        self.state = (0, 0)
        self.goal = (size - 1, size - 1)
        
    def reset(self) -> Tuple[int, int]:
        self.state = (0, 0)
        return self.state
        
    def step(self, action: str) -> Tuple[Tuple[int, int], float, bool, Dict[str, Any]]:
        x, y = self.state
        reward = -0.1  # Small penalty for each step to encourage efficiency
        done = False
        info = {"valid_action": True}
        
        # Calculate proposed new position
        new_x, new_y = x, y
        if action == "UP":
            new_y += 1
        elif action == "DOWN":
            new_y -= 1
        elif action == "RIGHT":
            new_x += 1
        elif action == "LEFT":
            new_x -= 1
        else:
            # Invalid action
            info["valid_action"] = False
            return self.state, -1.0, False, info

        # Boundary checks
        if 0 <= new_x < self.size and 0 <= new_y < self.size:
            self.state = (new_x, new_y)
        else:
            # Hit wall, stay in place, extra penalty
            reward = -1.0
            info["valid_action"] = False
            
        # Check Goal
        if self.state == self.goal:
            reward = 10.0
            done = True
            
        return self.state, reward, done, info

    def render(self):
        """Simple Text Render"""
        print("-" * (self.size + 2))
        for y in range(self.size - 1, -1, -1):
            row = "|"
            for x in range(self.size):
                if (x, y) == self.state:
                    row += "A"
                elif (x, y) == self.goal:
                    row += "G"
                else:
                    row += "."
            row += "|"
            print(row)
        print("-" * (self.size + 2))
