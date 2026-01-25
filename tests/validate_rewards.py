import asyncio
import logging
from environments.grid_world import GridWorld

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger("RewardValidator")

def run_scenario(name, actions, env):
    logger.info(f"--- Scenario: {name} ---")
    env.reset()
    total_reward = 0.0
    
    for i, action in enumerate(actions):
        state, reward, done, info = env.step(action)
        total_reward += reward
        logger.info(f"Step {i+1}: Action={action}, Reward={reward:.4f}, NewState={state}, Done={done}")
        if done:
            break
            
    logger.info(f"Total Reward: {total_reward:.4f}")
    return total_reward

def validate_rewards():
    env = GridWorld(size=5)
    # Grid is 5x5. Start (0,0), Goal (4,4).
    
    # Scenario 1: Optimal Path (8 steps)
    # Right x4, Up x4
    actions_optimal = ["RIGHT"] * 4 + ["UP"] * 4
    reward_optimal_1 = run_scenario("Optimal Path (Run 1)", actions_optimal, env)
    reward_optimal_2 = run_scenario("Optimal Path (Run 2)", actions_optimal, env)
    
    if reward_optimal_1 != reward_optimal_2:
        logger.error("FAILURE: Reward signal is non-deterministic!")
    else:
        logger.info("SUCCESS: Reward signal is deterministic.")

    # Scenario 2: Wall Hitting (Hugging bottom wall)
    # Down (hit), Down (hit), Right...
    actions_wall = ["DOWN", "DOWN", "RIGHT", "RIGHT"]
    run_scenario("Wall Hitting", actions_wall, env)

    # Scenario 3: Looping (Inefficient)
    # Right, Left, Right, Left...
    actions_loop = ["RIGHT", "LEFT", "RIGHT", "LEFT"]
    run_scenario("Looping", actions_loop, env)

if __name__ == "__main__":
    validate_rewards()
