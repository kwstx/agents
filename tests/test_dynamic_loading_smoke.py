import unittest
import sys
import os
import asyncio

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from environments.env_registry import EnvironmentRegistry
# Import directly to access the class-level log for assertions
from tests.dummy_plugins.dummy_agent import DummyAgent
from tests.dummy_plugins.dummy_env import DummyEnv

class MockMessageBus:
    def register(self, agent_id): return "token"
    def subscribe(self, topic, handler): pass

class TestDynamicLoadingSmoke(unittest.TestCase):
    def setUp(self):
        # Reset logs before each test
        DummyAgent.reset_log()
        DummyEnv.reset_log()

    def test_agent_loading_determinism(self):
        """
        Load and instantiate the dummy agent 10 times. 
        Verify initialization runs exactly once per instance.
        """
        print("\nTesting Agnet loading determinism (10 iterations)...")
        mock_bus = MockMessageBus()
        
        for i in range(10):
            agent_cls = AgentRegistry.load_agent("tests.dummy_plugins.dummy_agent", "DummyAgent")
            agent = agent_cls(agent_id=f"agent_{i}", message_bus=mock_bus)
            # We don't await start() here to keep it synchronous for this simple test, 
            # but we can verify init ran.
            self.assertIsInstance(agent, DummyAgent)
        
        # Verify log has 10 init entries
        self.assertEqual(len(DummyAgent.event_log), 10)
        for i in range(10):
            self.assertIn(f"init_agent_{i}", DummyAgent.event_log)
        
        print("Success: 10/10 agents loaded and initialized correctly.")

    def test_environment_loading_determinism(self):
        """
        Load and instantiate the dummy environment 10 times.
        Verify initialization runs exactly once per instance.
        """
        print("\nTesting Environment loading determinism (10 iterations)...")
        
        for i in range(10):
            env_cls = EnvironmentRegistry.load_environment("tests.dummy_plugins.dummy_env", "DummyEnv")
            env = env_cls()
            self.assertIsInstance(env, DummyEnv)
            env.reset()
            
        # Verify log has 10 init and 10 reset entries
        init_count = DummyEnv.event_log.count("init_env")
        reset_count = DummyEnv.event_log.count("reset_env")
        
        self.assertEqual(init_count, 10, "Expected 10 inits")
        self.assertEqual(reset_count, 10, "Expected 10 resets")
        
        print("Success: 10/10 environments loaded and initialized correctly.")

    def test_agent_lifecycle_hooks(self):
        """
        Verify agent setup hook runs.
        """
        print("\nTesting Agent lifecycle hooks...")
        async def run_lifecycle():
             agent_cls = AgentRegistry.load_agent("tests.dummy_plugins.dummy_agent", "DummyAgent")
             mock_bus = MockMessageBus()
             agent = agent_cls(agent_id="lifecycle_agent", message_bus=mock_bus)
             await agent.setup()
        
        asyncio.run(run_lifecycle())
        
        self.assertIn("init_lifecycle_agent", DummyAgent.event_log)
        self.assertIn("setup_lifecycle_agent", DummyAgent.event_log)
        print("Success: Agent lifecycle hooks executed.")

if __name__ == '__main__':
    unittest.main()
