import asyncio
import random
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine

class InvariantValidator:
    def __init__(self, size=5):
        self.size = size
    
    def check_continuity(self, prev, curr, step_idx):
        """Invariant: Agent can move at most 1 unit distance (Manhattan or Chebyshev)."""
        if prev is None:
            return True
            
        dx = abs(curr[0] - prev[0])
        dy = abs(curr[1] - prev[1])
        
        # In grid world, diagonal not allowed, so dx+dy <= 1. 
        # But even if it stays same (dx+dy=0), that's fine.
        is_valid = (dx + dy) <= 1
        
        if is_valid:
            print(f"[INVARIANT] Step {step_idx}: Continuity Check OK ({prev} -> {curr})")
        else:
            print(f"[ERROR] Step {step_idx}: Continuity VIOLATION! ({prev} -> {curr})")
            
        return is_valid

    def check_bounds(self, curr, step_idx):
        """Invariant: 0 <= coordinate < size."""
        x, y = curr
        is_valid = (0 <= x < self.size) and (0 <= y < self.size)
        
        if is_valid:
            print(f"[INVARIANT] Step {step_idx}: Bounds Check OK ({curr} in {self.size}x{self.size})")
        else:
            print(f"[ERROR] Step {step_idx}: Bounds VIOLATION! ({curr})")
            
        return is_valid

async def run_validation():
    print("Starting Invariant Validation...")
    
    env = GridWorld(size=5)
    engine = SimulationEngine(env, logger=None)
    agent_id = "ValidatorBot"
    validator = InvariantValidator(size=5)
    
    # Run a random walk
    prev_state = None
    curr_state = await engine.get_state(agent_id)
    
    # Check initial state
    assert validator.check_bounds(curr_state, 0), "Initial state out of bounds"
    
    actions = ["RIGHT", "UP", "LEFT", "DOWN", "RIGHT", "right", "INVALID", "UP", "UP"]
    
    for i, action in enumerate(actions):
        step_idx = i + 1
        print(f"\n--- Step {step_idx}: Action {action} ---")
        
        prev_state = curr_state
        await engine.perform_action(agent_id, action)
        curr_state = await engine.get_state(agent_id)
        
        # Assert Invariants
        valid_cont = validator.check_continuity(prev_state, curr_state, step_idx)
        valid_bound = validator.check_bounds(curr_state, step_idx)
        
        if not valid_cont or not valid_bound:
            print("FATAL: Invariant violated. Stopping.")
            exit(1)
            
    print("\nSUCCESS: All invariants held throughout the session.")

if __name__ == "__main__":
    asyncio.run(run_validation())
