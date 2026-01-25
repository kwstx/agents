import unittest
from environments.warehouse_env import WarehouseEnv

class TestWarehouseFidelity(unittest.TestCase):
    def setUp(self):
        self.env = WarehouseEnv(size=5, num_agents=2)
        # Manually verify dictionary reset/init for deterministic testing
        self.env.reset()

    def test_collision_enforcement(self):
        """Test that agents cannot occupy the same tile."""
        # Setup: Agent A at (0,0), Agent B at (0,1)
        self.env.agents["A"] = {"position": (0, 0), "battery": 100, "carrying": None}
        self.env.agents["B"] = {"position": (0, 1), "battery": 100, "carrying": None}
        
        # Action: A tries to move UP to (0,1)
        state, reward, done, info = self.env.step("UP", agent_id="A")
        
        # Expectation: Failure/Penalty
        self.assertEqual(state["position"], (0, 0), "Agent A should not have moved.")
        self.assertEqual(info.get("event"), "collision", "Event should be 'collision'.")
        self.assertLess(reward, 0, "Reward should be negative penalty.")

    def test_wall_clipping(self):
        """Test that agents cannot walk through walls."""
        self.env.agents["A"] = {"position": (0, 0), "battery": 100, "carrying": None}
        
        # Action: Move LEFT (into wall)
        state, reward, done, info = self.env.step("LEFT", agent_id="A")
        
        self.assertEqual(state["position"], (0, 0), "Agent should stay at (0,0).")
        self.assertLess(reward, -0.9, "Should receive wall hit penalty (-1.0).")

    def test_double_carrying(self):
        """Test that agents cannot pickup if already carrying."""
        # Setup: Agent at Pickup Zone (0,0) with package
        self.env.agents["A"] = {"position": (0, 0), "battery": 100, "carrying": "package"}
        
        # Action: Try to PICKUP again
        state, reward, done, info = self.env.step("PICKUP", agent_id="A")
        
        self.assertEqual(state["carrying"], "package", "Should still have one package.")
        self.assertNotEqual(info.get("event"), "picked_up", "Should not trigger pickup event.")
        self.assertLess(reward, 0, "Should be penalized for invalid action.")

    def test_teleportation_prevention(self):
        """Test that environment does not support 'TELEPORT' action."""
        self.env.agents["A"] = {"position": (0, 0), "battery": 100, "carrying": None}
        
        state, reward, done, info = self.env.step("TELEPORT", agent_id="A")
        
        self.assertEqual(state["position"], (0, 0))
        # Depending on base implementation, it might ignore or penalize.
        # Current implementation just does nothing for unknown actions, so pos stays (0,0).
        # Check reward (default time cost -0.1)
        self.assertEqual(reward, -0.1) 

if __name__ == '__main__':
    unittest.main()
