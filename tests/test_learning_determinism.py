import asyncio
import random
import numpy as np
import torch
import logging
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

# Silence logging for the test
logging.basicConfig(level=logging.ERROR)

async def run_training_session(seed: int, episodes: int = 20):
    # Set seeds
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    bus = MessageBus()
    await bus.start()
    env = GridWorld(size=5)
    
    agent = LearningGridAgent(f"Agent-{seed}", bus, env)
    agent.epsilon = 0.5 # Fixed epsilon to ensure some randomness usage
    
    rewards = []
    
    for _ in range(episodes):
        await agent._navigate_to_goal()
        rewards.append(agent.state["total_reward"])
        
    await bus.stop()
    return rewards

async def test_determinism():
    print("Test 1: Identical Seeds (42 vs 42)")
    results_a = await run_training_session(42)
    results_b = await run_training_session(42)
    
    if results_a == results_b:
        print("SUCCESS: Results matched for same seed.")
    else:
        print("FAILURE: Results DID NOT match for same seed!")
        print(f"A: {results_a[:5]}...")
        print(f"B: {results_b[:5]}...")
        
    print("\nTest 2: Different Seeds (42 vs 99)")
    results_c = await run_training_session(99)
    
    if results_a != results_c:
        print("SUCCESS: Results differed for different seed.")
    else:
        print("FAILURE: Results MATCHED for different seed (Unlikely but possible if deterministic logic is trivial).")
        
if __name__ == "__main__":
    asyncio.run(test_determinism())
