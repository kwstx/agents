import pytest
import asyncio
from typing import Any
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
        self.log_list.append(f"{self.name}: {reward}")
        return None

class RewardDoublingHook(AgentHook):
    """Doubles the reward."""
    def on_step_end(self, agent, state_vector, action_idx, reward, next_state_vector, done):
        return reward * 2.0

class TestModularHooks:
    @pytest.mark.asyncio
    async def test_hook_execution_and_reshaping(self):
        """Verify executing order and reward reshaping."""
        env = GridWorld(size=5)
        bus = MessageBus()
        model = GridDecisionModel()
        
        execution_log = []
        
        # Hooks: 
        # 1. Logger A (sees raw reward)
        # 2. Doubler (doubles reward)
        # 3. Logger B (sees doubled reward)
        
        hook_a = LoggingHook("A", execution_log)
        hook_double = RewardDoublingHook()
        hook_b = LoggingHook("B", execution_log)
        
        agent = LearningGridAgent("HookTestAgent", bus, env, model, hooks=[hook_a, hook_double, hook_b])
        agent.step_delay = 0
        
        # Force a step
        # We'll just run _navigate_to_goal for 1 step by mocking logic or just running it
        # Easier to just run it for a few steps
        
        task = asyncio.create_task(agent._navigate_to_goal())
        await asyncio.sleep(0.1) # Let it run briefly
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        # Check logs
        # Expected: A sees -0.1, B sees -0.2
        assert len(execution_log) > 0, "Hooks did not execute"
        
        first_entry = execution_log[0] # A: -0.1
        second_entry = execution_log[1] # B: -0.2
        
        assert "A: -0.1" in first_entry
        assert "B: -0.2" in second_entry
        
        # Verify Agent State has doubled reward 
        # (Since it sums up modified rewards)
        # If we ran for N steps, total reward should be N * -0.2
        
        assert agent.state["total_reward"] % 0.2 < 1e-9 , "Agent total reward should be multiple of -0.2"


    @pytest.mark.asyncio
    async def test_hot_swapping(self):
        """Verify adding/removing hooks at runtime."""
        env = GridWorld(size=5)
        bus = MessageBus()
        model = GridDecisionModel()
        
        log = []
        hook_a = LoggingHook("A", log)
        
        agent = LearningGridAgent("SwapAgent", bus, env, model, hooks=[hook_a])
        agent.step_delay = 0
        
        # Run step manually-ish or via public method
        # To avoid async complexities/cancelling, let's just inspect the logic or use a helper
        # We can simulate the loop logic by calling the hook loop directly if we could, 
        # but we are testing the integration.
        
        # Let's run navigate in background
        task = asyncio.create_task(agent._navigate_to_goal())
        await asyncio.sleep(0.1)
        
        # At this point log should have entries from A
        count_early = len(log)
        assert count_early > 0
        
        # REMOVE HOOK
        agent.hooks.remove(hook_a)
        log.append("REMOVED")
        
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except: pass
        
        # Check log
        # Should be: A, A, ..., REMOVED
        # No more A after REMOVED
        
        after_removed_entries = [e for e in log[count_early:] if "A:" in e]
        assert len(after_removed_entries) == 0, "Hook continued running after removal"
