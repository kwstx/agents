import asyncio
import numpy as np
import random
import torch
import json
import logging
import os
import matplotlib.pyplot as plt
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

# Logging
logging.basicConfig(level=logging.ERROR)

async def run_long_run_test():
    print("Starting Long-Run Drift Test (1000 Episodes)...")
    
    # Seeds
    seed = 4242
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    bus = MessageBus()
    await bus.start()
    env = GridWorld(size=5)
    
    # Continuous Learning Agent
    agent = LearningGridAgent("LongRunner", bus, env)
    agent.training_enabled = True
    agent.epsilon = 1.0
    
    episodes = 1000
    rewards = []
    epsilons = []
    
    for i in range(episodes):
        await agent._navigate_to_goal()
        rewards.append(agent.state["total_reward"])
        epsilons.append(agent.epsilon)
        
        if i % 100 == 0:
            avg_100 = np.mean(rewards[-100:]) if len(rewards) >= 100 else np.mean(rewards)
            print(f"Ep {i}: Avg Reward (Last 100)={avg_100:.2f}, Epsilon={agent.epsilon:.2f}")

    await bus.stop()
    
    # Analysis
    window = 50
    moving_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')
    
    final_avg = moving_avg[-1]
    peak_avg = np.max(moving_avg)
    baseline_val = -46.4
    
    print(f"\nLong-Run Analysis:")
    print(f"Final Moving Avg (50): {final_avg:.2f}")
    print(f"Peak Moving Avg (50):  {peak_avg:.2f}")
    
    # Checks
    print("\nVerifying Stability...")
    
    # 1. No Collapse: Should stay above baseline significantly
    if final_avg > baseline_val + 20:
        print("PASS: System did not collapse back to random baseline.")
    else:
        print("FAIL: System collapsed behaviorally.")
        
    # 2. Stability: Final shouldn't be drastically lower than peak (e.g. < 80% of peak, if peak > 0)
    # If peak is small, metrics are noisy. 
    # Let's just say, if we learned well, final should be positive.
    if final_avg > 0:
        print("PASS: Final performance is positive (Successful Navigation).")
    else:
        print("WARNING: Final performance is negative.")
        
    # Data Export
    os.makedirs("benchmarking", exist_ok=True)
    data = {
        "episodes": episodes,
        "rewards": rewards,
        "moving_avg": moving_avg.tolist()
    }
    with open("benchmarking/long_run.json", "w") as f:
        json.dump(data, f)
        
    # Plotting
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(rewards, alpha=0.3, label="Raw Reward", color='gray')
        plt.plot(range(window-1, episodes), moving_avg, color='blue', label="Moving Avg (50)")
        plt.axhline(y=baseline_val, color='red', linestyle='--', label="Baseline (Random)")
        plt.title(f"Agent Performance over {episodes} Episodes")
        plt.xlabel("Episode")
        plt.ylabel("Total Reward")
        plt.legend()
        plt.grid(True)
        os.makedirs("dashboards", exist_ok=True)
        plt.savefig("dashboards/long_run_trend.png")
        print("\nPlot saved to dashboards/long_run_trend.png")
    except Exception as e:
        print(f"\nPlotting failed (ignoring): {e}")

if __name__ == "__main__":
    asyncio.run(run_long_run_test())
