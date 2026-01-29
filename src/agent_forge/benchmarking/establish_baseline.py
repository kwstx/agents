import asyncio
import json
import os
import numpy as np
from agent_forge.agents.learning_agent import LearningGridAgent
from agent_forge.environments.grid_world import GridWorld
from agent_forge.utils.message_bus import MessageBus

async def run_baseline():
    print("Starting Baseline Establishment...")
    
    # Setup
    bus = MessageBus()
    await bus.start()
    env = GridWorld(size=5)
    
    # Agent with learning DISABLED and epsilon=1.0 (Pure Random)
    agent = LearningGridAgent("BaselineAgent", bus, env)
    agent.training_enabled = False
    agent.epsilon = 1.0 
    
    episodes = 100
    results = {
        "episodes": episodes,
        "successes": 0,
        "total_rewards": [],
        "steps_per_episode": []
    }
    
    for i in range(episodes):
        # Run episode
        transcript = await agent._navigate_to_goal()
        
        # Collect Metrics
        reward = agent.state["total_reward"]
        steps = len(transcript)
        
        # Did we reach the goal? 
        # GridWorld gives +10 reward for goal. 
        # Ideally, we check agent state or environment done flag, 
        # but here we can infer from high reward or check position.
        
        # Let's check position directly
        goal_reached = (agent.state["current_position"] == env.goal)
        
        results["total_rewards"].append(reward)
        results["steps_per_episode"].append(steps)
        if goal_reached:
            results["successes"] += 1
            
        if i % 10 == 0:
            print(f"Episode {i}: P={agent.state['current_position']}, R={reward:.2f}, S={steps}")

    # Compute Aggregates
    stats = {
        "success_rate": results["successes"] / episodes,
        "avg_reward": float(np.mean(results["total_rewards"])),
        "avg_steps": float(np.mean(results["steps_per_episode"])),
        "std_reward": float(np.std(results["total_rewards"])),
        "raw_data": results
    }
    
    print("\n--- Baseline Results ---")
    print(f"Success Rate: {stats['success_rate']*100:.1f}%")
    print(f"Avg Reward:   {stats['avg_reward']:.2f}")
    print(f"Avg Steps:    {stats['avg_steps']:.1f}")
    
    # Save to JSON
    os.makedirs("benchmarking", exist_ok=True)
    with open("benchmarking/baseline.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    # Generate Report
    generate_report(stats)
    
    await bus.stop()

def generate_report(stats):
    content = f"""# Non-Learning Baseline Report

**Date**: {os.environ.get('DATE', 'N/A')}
**Episodes**: {len(stats['raw_data']['total_rewards'])}

## Summary Metrics
- **Success Rate**: {stats['success_rate']*100:.1f}%
- **Average Reward**: {stats['avg_reward']:.2f}
- **Average Steps**: {stats['avg_steps']:.1f}
- **Reward StdDev**: {stats['std_reward']:.2f}

## Interpretation
These metrics represent the performance of a random-walk agent (`epsilon=1.0`, no training). 
Any trained agent must significantly outperform these numbers to demonstrate effective learning.

"""
    os.makedirs("dashboards", exist_ok=True)
    with open("dashboards/baseline_report.md", "w") as f:
        f.write(content)
    print("Report saved to dashboards/baseline_report.md")

if __name__ == "__main__":
    asyncio.run(run_baseline())
