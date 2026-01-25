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
        # Track state per agent: {agent_id: (x, y)}
        self.agents: Dict[str, Tuple[int, int]] = {}
        self.goal = (size - 1, size - 1)
        
    def reset(self, agent_id: str = "default") -> Tuple[int, int]:
        """Resets the specified agent to the starting position."""
        self.agents[agent_id] = (0, 0)
        return self.agents[agent_id]
        
    def step(self, action: str, agent_id: str = "default") -> Tuple[Tuple[int, int], float, bool, Dict[str, Any]]:
        if agent_id not in self.agents:
            self.reset(agent_id)
            
        x, y = self.agents[agent_id]
        reward = -0.1  # Small penalty
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
            info["valid_action"] = False
            return (x, y), -1.0, False, info

        # Boundary checks
        if 0 <= new_x < self.size and 0 <= new_y < self.size:
            # Check for collisions with other agents (optional, skipping for simple Co-op for now)
            # Actually, let's allow overlapping for now to avoid deadlocks in simple testing
            self.agents[agent_id] = (new_x, new_y)
        else:
            # Hit wall
            reward = -1.0
            info["valid_action"] = False
            
        # Check Goal
        if self.agents[agent_id] == self.goal:
            reward = 10.0
            done = True
            
        return self.agents[agent_id], reward, done, info

    def render(self):
        """Render the grid with all agents."""
        print("-" * (self.size + 2))
        for y in range(self.size - 1, -1, -1):
            row = "|"
            for x in range(self.size):
                cell = "."
                # Check for goal
                if (x, y) == self.goal:
                    cell = "G"
                # Check for agents
                agents_here = [aid for aid, pos in self.agents.items() if pos == (x, y)]
                if agents_here:
                    # Show first char of first agent ID if multiple
                    cell = agents_here[0][0].upper()
                    if len(agents_here) > 1:
                        cell = "+" # Multiple agents
                row += cell
            row += "|"
            print(row)
        print("-" * (self.size + 2))
