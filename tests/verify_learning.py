import asyncio
import logging
import os
import shutil
import numpy as np
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyLearning")

async def run_verification():
    # Cleanup previous models
    if os.path.exists("models/VerifyLearner_mlp.pth"):
        os.remove("models/VerifyLearner_mlp.pth")

    logger.info("Initializing Environment and Agent...")
    bus = MessageBus()
    await bus.start()
    
    env = GridWorld(size=5)
    agent = LearningGridAgent("VerifyLearner", bus, env)
    
    rewards = []
    episodes = 50
    
    logger.info(f"Starting {episodes} training episodes...")
    
    for i in range(episodes):
        transcript = await agent._navigate_to_goal()
        total_reward = agent.state["total_reward"]
        rewards.append(total_reward)
        
        if i % 10 == 0:
            logger.info(f"Episode {i}: Reward = {total_reward}, Epsilon = {agent.epsilon:.2f}")
            
    avg_first_10 = np.mean(rewards[:10])
    avg_last_10 = np.mean(rewards[-10:])
    
    logger.info(f"Average Reward (First 10): {avg_first_10}")
    logger.info(f"Average Reward (Last 10): {avg_last_10}")
    
    # Check for model checkpoint
    if os.path.exists("models/VerifyLearner_mlp.pth"):
        logger.info("SUCCESS: Model checkpoint found.")
    else:
        logger.error("FAILURE: Model checkpoint NOT found.")
        
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_verification())
