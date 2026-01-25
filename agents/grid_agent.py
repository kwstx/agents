import asyncio
from typing import Any, List
from agents.base_agent import BaseAgent
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

class GridAgent(BaseAgent):
    """
    An agent capable of navigating the GridWorld environment.
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, env: GridWorld):
        super().__init__(agent_id, message_bus)
        self.env = env
        self.state["env_type"] = "GridWorld"
        self.state["current_position"] = None
        self.state["total_reward"] = 0.0
        self.step_delay = 0.1 # Default delay for visualization

    async def process_task(self, task: Any) -> Any:
        if task == "navigate_to_goal":
            return await self._navigate_to_goal()
        elif task == "random_walk":
             # Placeholder for other behaviors
             pass
        return f"Unknown task: {task}"

    async def _navigate_to_goal(self) -> List[str]:
        """
        Executes a simple policy to reach the goal.
        """
        obs = self.env.reset()
        self.state["current_position"] = obs
        self.state["total_reward"] = 0.0
        
        # Log initial state
        self.save_checkpoint("navigate_to_goal", "started")
        
        done = False
        steps = 0
        transcript = []
        max_steps = 20
        
        target_x, target_y = self.env.goal # accessing public attribute of GridWorld
        
        self.logger.info(f"Starting navigation from {obs} to {self.env.goal}")

        while not done and steps < max_steps:
            current_x, current_y = self.state["current_position"]
            
            # Simple policy: Move towards goal
            action = "STAY"
            if current_x < target_x:
                action = "RIGHT"
            elif current_y < target_y:
                action = "UP"
            elif current_x > target_x:
                action = "LEFT"
            elif current_y > target_y: 
                action = "DOWN"
            
            # Execute action
            obs, reward, done, info = self.env.step(action)
            
            # Update state
            self.state["current_position"] = obs
            self.state["total_reward"] += reward
            self.state["last_action"] = action
            self.state["last_step_info"] = info
            
            step_summary = f"Step {steps}: Action={action}, Pos={obs}, Reward={reward}, Done={done}"
            transcript.append(step_summary)
            self.logger.info(step_summary)
            
            # Checkpoint for dashboard visualization
            # We explicitly save here to get frame-by-frame visualization potential
            self.save_checkpoint("navigate_to_goal", {"step": steps, "action": action, "reward": reward})
            
            
            steps += 1
            if self.step_delay > 0:
                await asyncio.sleep(self.step_delay)

        final_status = "Success" if done else "Max steps reached"
        self.logger.info(f"Navigation finished: {final_status}")
        
        if done:
             await self.send_message("goal_reached", {"position": obs, "steps": steps})
             
        return transcript
