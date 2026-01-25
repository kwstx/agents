import asyncio
import traceback
from agents.hooks import AgentHook
from agents.learning_agent import LearningGridAgent
from models.decision_model import GridDecisionModel
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

class LoggingHook(AgentHook):
    def __init__(self, name, log_list):
        self.name = name
        self.log_list = log_list
        
    def on_step_end(self, agent, state_vector, action_idx, reward, next_state_vector, done):
        print(f"Hook {self.name} called with reward {reward}")
        self.log_list.append(f"{self.name}: {reward}")
        return None

async def run():
    try:
        print("Initializing...")
        env = GridWorld(size=5)
        bus = MessageBus()
        model = GridDecisionModel()
        
        execution_log = []
        hook_a = LoggingHook("A", execution_log)
        
        agent = LearningGridAgent("HookDebug", bus, env, model, hooks=[hook_a])
        
        print("Starting navigation...")
        # Run one full episode
        transcript = await agent._navigate_to_goal()
        
        print(f"Transcript length: {len(transcript)}")
        print(f"Log length: {len(execution_log)}")
        
        if len(execution_log) == 0:
            print("FAILURE: No logs captured.")
        else:
            print("SUCCESS: Logs captured.")
            print(execution_log[:3])
            
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
