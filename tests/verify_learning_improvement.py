import asyncio
import numpy as np
import matplotlib.pyplot as plt
import torch
import random
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus
from agents.hooks import DQNTrainHook

async def run_baseline(episodes=100):
    """Runs a random policy baseline."""
    env = GridWorld(size=5)
    env.reset()
    rewards = []
    
    for _ in range(episodes):
        env.reset()
        done = False
        total_reward = 0
        steps = 0
        while not done and steps < 50:
            # Random action
            action = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            _, reward, done, _ = env.step(action)
            total_reward += reward
            steps += 1
        rewards.append(total_reward)
        
    return rewards

async def run_training(episodes=400):
    """Runs the training loop."""
    env = GridWorld(size=5)
    bus = MessageBus()
    # High learning rate for fast conversion in this small env
    config = ModelConfig(learning_rate=0.005) 
    model = GridDecisionModel(config)
    trainer = DQNTrainer(model, config)
    train_hook = DQNTrainHook(trainer)
    
    agent = LearningGridAgent("Learner-Test", bus, env, model, hooks=[train_hook])
    # Constant-ish decay
    agent.epsilon = 1.0
    agent.epsilon_decay = 0.99
    agent.step_delay = 0 # Run at max speed
    
    rewards = []
    
    for i in range(episodes):
        transcript = await agent._navigate_to_goal()
        rewards.append(agent.state["total_reward"])
        
    return rewards

async def main():
    import logging
    logging.disable(logging.CRITICAL) 
    
    print("Running Baseline (Random Policy)...")
    baseline_rewards = await run_baseline(episodes=100)
    baseline_avg = np.mean(baseline_rewards)
    print(f"Baseline Average Reward: {baseline_avg:.2f}")

    print("Running Training Agent (400 episodes)...")
    training_rewards = await run_training(episodes=400)
    
    # Evaluate last 50 episodes of training (simulating 'learned' state)
    training_final_avg = np.mean(training_rewards[-50:])
    print(f"Trained Agent Average Reward (Last 50 eps): {training_final_avg:.2f}")
    
    # Statistical/Heuristic Check
    improvement_ratio = training_final_avg - baseline_avg
    print(f"Improvement Margin: {improvement_ratio:.2f}")
    
    assert training_final_avg > baseline_avg + 2.0, f"Learning gain insufficient: {improvement_ratio:.2f}"
    
    print("SUCCESS: Learning verified. Agent significantly outperforms baseline.")

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.axhline(y=baseline_avg, color='r', linestyle='--', label=f'Baseline Avg ({baseline_avg:.2f})')
    plt.plot(training_rewards, label='Training Rewards')
    # Moving average
    window = 10
    mov_avg = np.convolve(training_rewards, np.ones(window)/window, mode='valid')
    plt.plot(range(window-1, len(training_rewards)), mov_avg, color='orange', label='Moving Avg (10)')
    
    plt.title("Learning Validation: Trained Agent vs Random Baseline")
    plt.xlabel("Episode")
    plt.ylabel("Total Reward")
    plt.legend()
    plt.grid(True)
    plt.savefig("learning_vs_baseline.png")
    print("Comparison plot saved to learning_vs_baseline.png")

if __name__ == "__main__":
    asyncio.run(main())
