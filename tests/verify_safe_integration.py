import asyncio
import json
import os
import torch
import numpy as np
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus
from models.decision_model import GridDecisionModel, ModelConfig

async def verify_safe_integration():
    print("Starting Safe Integration Verification...")
    
    # 1. Load Baseline Data
    print("Loading Baseline...")
    try:
        with open("benchmarking/baseline.json", "r") as f:
            baseline = json.load(f)
    except FileNotFoundError:
        print("FAILURE: benchmarks/baseline.json not found. Run establishing_baseline.py first.")
        return

    baseline_success_rate = baseline["success_rate"]
    baseline_avg_reward = baseline["avg_reward"]
    
    print(f"Baseline Success Rate: {baseline_success_rate*100:.1f}%")
    print(f"Baseline Avg Reward: {baseline_avg_reward:.2f}")

    # 2. Setup Agent with Trained Model
    print("Loading Trained Model...")
    model_path = "models/VerifyLearner_mlp.pth"
    if not os.path.exists(model_path):
        print(f"FAILURE: Model {model_path} not found.")
        return
        
    bus = MessageBus()
    await bus.start()
    env = GridWorld(size=5)
    
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
    model.load_state_dict(torch.load(model_path))
    model.eval() # Set to evaluation mode
    
    agent = LearningGridAgent("RefinedAgent", bus, env, model=model)
    agent.training_enabled = False
    agent.epsilon = 0.0 # Greedy, no exploration
    
    # 3. Run Validation Episodes
    episodes = 20
    rewards = []
    successes = 0
    
    print(f"Running {episodes} validation episodes...")
    
    for i in range(episodes):
        await agent._navigate_to_goal()
        reward = agent.state["total_reward"]
        rewards.append(reward)
        
        goal_reached = (agent.state["current_position"] == env.goal)
        if goal_reached:
            successes += 1
            
        if i % 5 == 0:
             print(f"Episode {i}: Reward={reward:.2f}, Goal={goal_reached}")
             
    refined_avg_reward = float(np.mean(rewards))
    refined_success_rate = successes / episodes
    
    print(f"\nRefined Success Rate: {refined_success_rate*100:.1f}%")
    print(f"Refined Avg Reward: {refined_avg_reward:.2f}")
    
    await bus.stop()
    
    # 4. Compare and Assert
    print("\n--- Comparative Analysis ---")
    
    # Check 1: Success Rate Improvement
    if refined_success_rate >= baseline_success_rate:
        print("SUCCESS: Refined agent matches or beats baseline success rate.")
    else:
        print("WARNING: Refined agent success rate is LOWER than baseline.")
        
    # Check 2: Reward Improvement
    if refined_avg_reward > baseline_avg_reward:
         print("SUCCESS: Refined agent achieves higher average reward.")
    else:
         print("WARNING: Refined agent reward is NOT higher than baseline.")

    # Check 3: Safety (Heuristic: Average reward shouldn't be catastrophic)
    # Baseline was -46.4 from random walking. If we are worse than that, it's bad.
    if refined_avg_reward < -50.0:
        print("FAILURE: Safety Regression detected! Reward is catastrophically low.")
    else:
        print("SUCCESS: Safety check passed (Reward is within reasonable bounds).")

    # Overall Verdict
    if refined_avg_reward > baseline_avg_reward and refined_success_rate >= baseline_success_rate:
        print("\nOVERALL: IMPROVEMENT CONFIRMED")
    else:
        print("\nOVERALL: NO CLEAR IMPROVEMENT (Need more training?)")

if __name__ == "__main__":
    asyncio.run(verify_safe_integration())
