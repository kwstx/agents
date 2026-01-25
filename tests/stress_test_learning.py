import asyncio
import numpy as np
import random
import torch
import logging
from agents.learning_agent import LearningGridAgent
from environments.noisy_grid_world import NoisyGridWorld
from utils.message_bus import MessageBus

# Logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("StressTestLearning")
logger.setLevel(logging.INFO)

async def run_resilience_test():
    print("Starting Resilience Learning Test (Slippery Floor)...")
    
    # 1. Baseline: Untrained Agent on Noisy Environment
    # If the floor is slippery, random walk should be even worse or equally bad.
    bus = MessageBus()
    await bus.start()
    env = NoisyGridWorld(size=5, slippery_prob=0.25) # 25% slip chance
    
    # Force seed for fairness in comparison (though slip is random)
    random.seed(123)
    np.random.seed(123)
    torch.manual_seed(123)
    
    baseline_rewards = []
    print("\nPhase 1: Baseline (Random Agent in Chaos)...")
    agent_baseline = LearningGridAgent("ChaosWalker", bus, env)
    agent_baseline.training_enabled = False
    agent_baseline.epsilon = 1.0
    
    for i in range(20):
        await agent_baseline._navigate_to_goal()
        baseline_rewards.append(agent_baseline.state["total_reward"])
        
    avg_base = np.mean(baseline_rewards)
    print(f"Baseline Avg Reward: {avg_base:.2f}")
    
    # 2. Training: Learning Agent on Noisy Environment
    print("\nPhase 2: Training (Learning to Skate)...")
    
    # Reset seeds for clean start
    random.seed(123)
    np.random.seed(123)
    torch.manual_seed(123)
    
    env_train = NoisyGridWorld(size=5, slippery_prob=0.25)
    agent_learner = LearningGridAgent("SkaterAgent", bus, env_train)
    agent_learner.training_enabled = True
    agent_learner.epsilon = 1.0 # Start with exploration
    
    training_episodes = 200
    training_rewards = []
    
    for i in range(training_episodes):
        await agent_learner._navigate_to_goal()
        training_rewards.append(agent_learner.state["total_reward"])
        if i % 50 == 0:
            print(f"Training Ep {i}: Reward={training_rewards[-1]:.2f}, Epsilon={agent_learner.epsilon:.2f}")

    # 3. Validation: Trained Agent on Noisy Environment (Greedy)
    print("\nPhase 3: Validation (Greedy Execution)...")
    agent_learner.training_enabled = False
    agent_learner.epsilon = 0.05 # Small epsilon for slight flexibility, or 0 for greedy
    
    val_rewards = []
    successes = 0
    episodes_val = 20
    
    for i in range(episodes_val):
        await agent_learner._navigate_to_goal()
        reward = agent_learner.state["total_reward"]
        val_rewards.append(reward)
        
        if agent_learner.state["current_position"] == env_train.goal:
            successes += 1
            
    avg_val = np.mean(val_rewards)
    success_rate = successes / episodes_val
    
    print(f"\nResilience Results:")
    print(f"Baseline (Random): {avg_base:.2f}")
    print(f"Trained (Skater):  {avg_val:.2f}")
    print(f"Success Rate:      {success_rate*100:.1f}%")
    
    # Assertions
    if avg_val > avg_base + 5.0: # Significant improvement
        print("\nSUCCESS: Agent learned to cope with slippery terrain.")
    else:
        print("\nFAILURE: Agent did not improve significantly.")
        
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_resilience_test())
