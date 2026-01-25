import asyncio
import matplotlib.pyplot as plt
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer
from agents.learning_agent import LearningGridAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

async def run_training():
    print("Initializing Training...")
    
    # Setup
    env = GridWorld(size=5)
    bus = MessageBus()
    config = ModelConfig(learning_rate=0.005)
    model = GridDecisionModel(config)
    trainer = DQNTrainer(model, config)
    
    # Create hooks
    from agents.hooks import DQNTrainHook
    train_hook = DQNTrainHook(trainer)
    
    agent = LearningGridAgent("Learner-01", bus, env, model, hooks=[train_hook])
    
    episodes = 200
    rewards_history = []
    
    print(f"Starting {episodes} episodes...")
    
    for e in range(episodes):
        transcript = await agent.process_task("navigate_to_goal")
        total_reward = agent.state["total_reward"]
        rewards_history.append(total_reward)
        
        if (e + 1) % 10 == 0:
            print(f"Episode {e+1}/{episodes} - Reward: {total_reward:.2f} - Epsilon: {agent.epsilon:.2f}")
            
    # Save Model
    trainer.save_model("models/grid_mlp.pth")
    print("Model saved to models/grid_mlp.pth")
    
    # Plot results
    plt.plot(rewards_history)
    plt.title("Agent Training Progress")
    plt.xlabel("Episode")
    plt.ylabel("Total Reward")
    plt.savefig("training_plot.png")
    print("Training plot saved to training_plot.png")

if __name__ == "__main__":
    asyncio.run(run_training())
