
import random
from typing import List, Tuple, Any
from agent_forge.agents.grid_agent import GridAgent
from agent_forge.utils.message_bus import MessageBus
from agent_forge.environments.grid_world import GridWorld

class CollaborativeExplorerAgent(GridAgent):
    """
    An agent that explores grid efficiently by sharing visited locations.
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, env: GridWorld):
        super().__init__(agent_id, message_bus, env)
        self.global_visited = set()
        
    async def setup(self):
        """Subscribe to exploration updates."""
        self.subscribe("exploration_update")

    async def receive_message(self, message):
        """Handle incoming messages."""
        await super().receive_message(message)
        
        if message.topic == "exploration_update":
            if message.sender != self.agent_id:
                pos = tuple(message.payload["pos"])
                if pos not in self.global_visited:
                    self.global_visited.add(pos)
                    # self.logger.info(f"Learned that {message.sender} visited {pos}")

    def select_action(self, current_pos: Tuple[int, int]) -> str:
        """
        Choose action to prefer unvisited nodes.
        """
        x, y = current_pos
        self.global_visited.add((x, y)) # Mark current as visited
        
        # Determine valid moves
        moves = [
            ("UP", (x, y + 1)),
            ("DOWN", (x, y - 1)),
            ("LEFT", (x - 1, y)),
            ("RIGHT", (x + 1, y))
        ]
        
        valid_moves = []
        for action, pos in moves:
            nx, ny = pos
            if 0 <= nx < self.env.size and 0 <= ny < self.env.size:
                valid_moves.append((action, pos))
                
        if not valid_moves:
            return "STAY"
            
        # Filter for unvisited
        unvisited_moves = [(act, pos) for act, pos in valid_moves if pos not in self.global_visited]
        
        if unvisited_moves:
            # Pick one
            action, target_pos = random.choice(unvisited_moves)
            self.logger.info(f"Choosing {action} to explore unvisited {target_pos}")
            return action
        else:
            # All neighbors visited, pick random but log it
            action, target_pos = random.choice(valid_moves)
            self.logger.info(f"All neighbors visited. Wandering {action} to {target_pos} (Avoiding nothing)")
            return action
            
    async def on_step_complete(self, new_pos):
        """Called after a step is taken."""
        self.global_visited.add(new_pos)
        await self.send_message("exploration_update", {"pos": new_pos})
