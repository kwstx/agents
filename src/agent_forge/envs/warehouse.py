from typing import Any, Tuple, Dict, List
import random
import time
from agent_forge.core.base_env import BaseEnvironment

class WarehouseEnv(BaseEnvironment):
    """
    Warehouse environment with logistics tasks.
    State per agent: {
        "position": (x, y),
        "battery": float (0-100),
        "carrying": Optional[str]  # None or "item_A", "item_B"
    }
    """
    
    def __init__(self, size: int = 10, num_agents: int = 3, config: Dict[str, Any] = None):
        self.size = size
        self.num_agents = num_agents
        self.config = config or {}
        self.battery_drain_rate = self.config.get("battery_drain_rate", 2.0) # per second
        self.safety_rails = self.config.get("safety_rails", False) # If False, allows out-of-bounds
        
        self.agents = {} # agent_id -> state dict
        
        # Define Zones
        # Simple layout: 
        # Left column (x=0) = Pickup
        # Right column (x=size-1) = Dropoff
        # Top row (y=size-1) = Charging
        self.zones = {
            "pickup": [(0, y) for y in range(size)],
            "dropoff": [(size-1, y) for y in range(size)],
            "charger": [(x, size-1) for x in range(size)]
        }
        
    def reset(self) -> Dict[str, Any]:
        """Resets all agents to random positions."""
        self.agents = {}
        # We assume specific agent IDs will be passed in step, OR we pre-seed them.
        # But reset typically returns initial state. 
        # In multi-agent, maybe return a dict of states?
        # For compatibility with SimulationEngine which expects single state return from reset...
        # We'll return a global view or just None implies "call get_state(agent_id)"
        return {} 

    def get_agent_state(self, agent_id: str):
        """Helper to init or get state with collision-free spawning."""
        if agent_id not in self.agents:
            # Gather all occupied positions
            occupied = {s["position"] for s in self.agents.values()}
            
            # Try to find a free spot
            # Simple rejection sampling with fallback
            pos = None
            for _ in range(100):
                # Don't spawn in pickup/dropoff columns to avoid immediate congestion
                # Spawn in middle area x=[1, size-2]
                rx = random.randint(1, self.size-2)
                ry = random.randint(0, self.size-1)
                candidate = (rx, ry)
                if candidate not in occupied:
                    pos = candidate
                    break
            
            if pos is None:
                # Fallback: Just pick random valid spot even if occupied (shouldn't happen with reasonable density)
                pos = (random.randint(1, self.size-2), random.randint(0, self.size-1))
                
            self.agents[agent_id] = {
                "position": pos,
                "battery": 100.0,
                "carrying": None,
                "server_time": time.time()
            }
        else:
            # Do not update server_time on fetch; only on state change
            pass
            
        return self.agents[agent_id]

    def step(self, action: str, agent_id: str = "default") -> Tuple[Any, float, bool, Dict[str, Any]]:
        state = self.get_agent_state(agent_id)
        x, y = state["position"]
        battery = state["battery"]
        carrying = state["carrying"]
        last_time = state.get("server_time", time.time())
        current_time = time.time()
        
        reward = -0.1 # Time cost
        done = False
        info = {"valid_action": True, "old_pos": (x, y)}
        
        # Battery cost (Time-based)
        duration = current_time - last_time
        # Ensure at least some cost if duration is tiny (e.g. unit test speed)
        time_cost = max(0.01, duration) * self.battery_drain_rate
        battery -= time_cost
        
        # Movement
        new_x, new_y = x, y
        if action == "UP": new_y += 1
        elif action == "DOWN": new_y -= 1
        elif action == "RIGHT": new_x += 1
        elif action == "LEFT": new_x -= 1
        elif action == "PICKUP":
            if (x, y) in self.zones["pickup"] and carrying is None:
                carrying = "package"
                reward += 1.0
                info["event"] = "picked_up"
            else:
                reward -= 0.5 # Illegal move
        elif action == "DROPOFF":
            if (x, y) in self.zones["dropoff"] and carrying is not None:
                carrying = None
                reward += 10.0 # Delivery Success
                info["event"] = "delivered"
            else:
                reward -= 0.5
        elif action == "CHARGE":
            if (x, y) in self.zones["charger"]:
                battery = min(100.0, battery + 10.0)
                # Staying to charge costs time but gains battery
            else:
                reward -= 0.5
        

        # Boundary Check
        # If safety_rails is True, we clamp. If False, we allow out-of-bounds (for Auditors to catch).
        if self.safety_rails:
            if 0 <= new_x < self.size and 0 <= new_y < self.size:
               pass # Valid
            else:
               # Hit wall, reset
               new_x, new_y = x, y
               reward -= 1.0
        
        # Update Position
        state["position"] = (new_x, new_y)
        state["server_time"] = current_time # Update time

        # Update State
        state["battery"] = battery
        state["carrying"] = carrying
        self.agents[agent_id] = state
        
        if battery <= 0:
            done = True # Agent dead
            reward -= 10.0
            info["event"] = "battery_depleted"
            
        return state, reward, done, info

    def render(self):
        # Text render of grid?
        pass
