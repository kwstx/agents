import unittest
import asyncio
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine

class TestSimulationAPI(unittest.TestCase):
    def setUp(self):
        self.env = GridWorld(size=5)
        # No stress, no logging - pure logic test
        self.engine = SimulationEngine(self.env, logger=None, stress_config={})
        self.agent_id = "UnitTester"

    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_get_state_initial(self):
        """Test that get_state returns the correct initial state."""
        state = self.run_async(self.engine.get_state(self.agent_id))
        self.assertEqual(state, (0, 0), "Initial state should be (0,0)")

    def test_get_state_consistency(self):
        """Test that get_state is consistent for different calls."""
        state1 = self.run_async(self.engine.get_state("AgentA"))
        state2 = self.run_async(self.engine.get_state("AgentB"))
        self.assertEqual(state1, state2, "State should be shared/consistent in this MVP")

    def test_perform_action_valid(self):
        """Test a valid move updates state correctly."""
        success = self.run_async(self.engine.perform_action(self.agent_id, "RIGHT"))
        self.assertTrue(success, "Action should succeed")
        
        state = self.run_async(self.engine.get_state(self.agent_id))
        self.assertEqual(state, (1, 0), "Agent should have moved right to (1,0)")

    def test_perform_action_wall(self):
        """Test hitting a wall stays in place and gives penalty."""
        # Try moving LEFT from (0,0)
        success = self.run_async(self.engine.perform_action(self.agent_id, "LEFT"))
        self.assertTrue(success, "Simulation continues even if wall hit")
        
        state = self.run_async(self.engine.get_state(self.agent_id))
        self.assertEqual(state, (0, 0), "Agent should remain at (0,0)")
        
        feedback = self.run_async(self.engine.get_feedback(self.agent_id))
        self.assertEqual(feedback["reward"], -1.0, "Should receive wall penalty")

    def test_perform_action_invalid_command(self):
        """Test sending nonsense action."""
        success = self.run_async(self.engine.perform_action(self.agent_id, "JUMP_AROUND"))
        self.assertTrue(success, "Sim logic handles invalid action by staying put usually")
        
        state = self.run_async(self.engine.get_state(self.agent_id))
        self.assertEqual(state, (0, 0))
        
        feedback = self.run_async(self.engine.get_feedback(self.agent_id))
        self.assertEqual(feedback["reward"], -1.0, "GridWorld penalizes invalid actions with -1.0")
        self.assertFalse(feedback["info"]["valid_action"], "Info should mark action as invalid")

    def test_goal_condition(self):
        """Test reaching the goal."""
        # State goal for 5x5 is (4,4)
        # Move to (4,3)
        self.env.state = (4, 3) # Cheat to get close
        self.engine._current_observation = (4, 3) # Sync engine cache
        
        # Move UP to (4,4)
        success = self.run_async(self.engine.perform_action(self.agent_id, "UP"))
        
        # Should be done
        self.assertFalse(success, "Perform action returns True for 'continue', False for 'done'") 
        # Wait, GridWorld returns Done=True when goal reached. 
        # Engine perform_action returns 'not done'. 
        # So done=True -> return False. Correct.

        feedback = self.run_async(self.engine.get_feedback(self.agent_id))
        self.assertEqual(feedback["reward"], 10.0, "Goal reward")
        self.assertTrue(feedback["done"], "Done flag set")

    def test_action_after_done(self):
        """Test attempting action after simulation is over."""
        # Force done
        self.engine._last_done = True
        
        success = self.run_async(self.engine.perform_action(self.agent_id, "RIGHT"))
        self.assertFalse(success, "Should fail/return False if already done")
        
        # Ensure state didn't change
        state = self.run_async(self.engine.get_state(self.agent_id))
        self.assertEqual(state, (0,0), "State should not change after done")

if __name__ == '__main__':
    unittest.main()
