import asyncio
import numpy as np
import random
import torch
import json
import logging
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from environments.noisy_grid_world import NoisyGridWorld
from utils.message_bus import MessageBus

# Logging
logging.basicConfig(level=logging.ERROR)

async def run_transfer_test():
    print("Starting Transfer Learning Test (Robustness Generalization)...")
    
    # Setup seeds
    seed = 555
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    bus = MessageBus()
    await bus.start()
    
    # 1. Train on STRESS Environment
    print("\nPhase 1: Training on Stress Environment (Slippery Floor)...")
    stress_env = NoisyGridWorld(size=5, slippery_prob=0.25)
    robust_agent = LearningGridAgent("RobustAgent", bus, stress_env)
    robust_agent.training_enabled = True
    robust_agent.epsilon = 1.0
    
    # Train for 200 episodes
    for i in range(200):
        await robust_agent._navigate_to_goal()
        if i % 100 == 0:
            print(f"Training Ep {i}: Reward={robust_agent.state['total_reward']:.2f}")

    print("Training Complete.")
    
    # 2. Transfer to NORMAL Environment
    print("\nPhase 2: Transferring to Normal Environment (Clean Floor)...")
    normal_env = GridWorld(size=5)
    
    # We use the SAME agent instance, but switch the environment reference
    # In a real app, we'd save/load model, but here swapping env object is fine for test
    robust_agent.env = normal_env
    robust_agent.training_enabled = False # Stop updating weights (Evaluation Mode)
    robust_agent.epsilon = 0.0 # Greedy
    
    # 3. Evaluate
    print("Evaluating Performance...")
    rewards = []
    successes = 0
    episodes = 20
    
    for i in range(episodes):
        await robust_agent._navigate_to_goal()
        reward = robust_agent.state["total_reward"]
        rewards.append(reward)
        
        if robust_agent.state["current_position"] == normal_env.goal:
            successes += 1
            
        if i % 5 == 0:
             print(f"Eval Ep {i}: Reward={reward:.2f}")

    avg_reward = np.mean(rewards)
    success_rate = successes / episodes
    
    print(f"\nRobust Agent Results on Normal World:")
    print(f"Avg Reward: {avg_reward:.2f}")
    print(f"Success Rate: {success_rate*100:.1f}%")
    
    # 4. Compare with Baseline (Untrained Agent on Normal World)
    # Load baseline value
    try:
        with open("benchmarking/baseline.json", "r") as f:
            baseline_data = json.load(f)
            baseline_reward = baseline_data["avg_reward"]
    except:
        baseline_reward = -46.4 # Fallback known value
        
    print(f"Baseline (Untrained) Reward: {baseline_reward:.2f}")

    # Assertions
    if avg_reward > baseline_reward + 20: 
        print("\nSUCCESS: Robust Agent significantly outperforms Untrained Baseline.")
        print("Transfer Learning Confirmed: The agent learned a policy in stress that works in normal conditions.")
    else:
        print("\nFAILURE: Robust Agent did not outperform baseline significantly.")
        
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_transfer_test())
