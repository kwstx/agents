import asyncio
from typing import List
from agent_forge.agents.grid_agent import GridAgent
from agent_forge.environments.simulation_engine import SimulationEngine
from agent_forge.utils.message_bus import MessageBus

class SimGridAgent(GridAgent):
    """
    Adapter agent that uses the SimulationEngine (Async) instead of direct GridWorld (Sync).
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, engine: SimulationEngine):
        # We pass engine as 'env', though base class expects GridWorld, we override usage.
        # Python duck typing :) But better to be explicit in overriding methods.
        super().__init__(agent_id, message_bus, env=engine)
        self.engine = engine # Alias for clarity

    async def _navigate_to_goal(self) -> List[str]:
        """
        Modified navigation policy to use Async SimulationEngine.
        """
        # Initial State
        obs = await self.engine.get_state(self.agent_id) # Async call!
        self.state["current_position"] = obs
        self.state["total_reward"] = 0.0
        
        self.save_checkpoint("navigate_to_goal", "started")
        
        done = False
        steps = 0
        transcript = []
        max_steps = 20
        
        # Access goal from the underlying env
        target_x, target_y = self.engine.env.goal 
        
        self.logger.info(f"Starting navigation from {obs} to {self.engine.env.goal} (Via Async Engine)")

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
            
            # Execute action via Engine (Async)
            # Perform Action returns Success/Fail (bool), not the full tuple
            action_success = await self.engine.perform_action(self.agent_id, action)
            
            # Get Feedback
            feedback = await self.engine.get_feedback(self.agent_id)
            reward = feedback["reward"]
            done = feedback["done"]
            info = feedback["info"]
            
            # Get New State
            obs = await self.engine.get_state(self.agent_id)
            
            # Update state
            self.state["current_position"] = obs
            self.state["total_reward"] += reward
            self.state["last_action"] = action
            self.state["last_step_info"] = info
            
            step_summary = f"Step {steps}: Action={action}, Pos={obs}, Reward={reward}, Done={done}"
            transcript.append(step_summary)
            self.logger.info(step_summary)
            
            self.save_checkpoint("navigate_to_goal", {"step": steps, "action": action, "reward": reward})
            
            steps += 1
            # SimulationEngine already has latency, so no need for extra sleep here unless for visualization pacing
            
        final_status = "Success" if done else "Max steps reached"
        self.logger.info(f"Navigation finished: {final_status}")
        
        if done:
             await self.send_message("goal_reached", {"position": obs, "steps": steps})
             
        return transcript
