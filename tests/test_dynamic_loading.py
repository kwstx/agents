import sys
import os
import unittest

# Ensure the project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from environments.env_registry import EnvironmentRegistry

class MockMessageBus:
    def register(self, agent_id): return "token"
    def subscribe(self, topic, handler): pass

class TestDynamicLoading(unittest.TestCase):
    def test_load_finance_agent(self):
        print("\nTesting dynamic load of FinanceAgent...")
        agent_cls = AgentRegistry.load_agent("agents.finance_agent", "FinanceAgent")
        mock_bus = MockMessageBus()
        agent = agent_cls(agent_id="fin_bot_1", message_bus=mock_bus)
        self.assertEqual(agent.agent_id, "fin_bot_1")
        decision = agent.decide({"sentiment": "bullish", "price": 100})
        print(f"FinanceAgent decision: {decision}")
        self.assertEqual(decision["action"], "buy")

    def test_load_robotics_sim(self):
        print("\nTesting dynamic load of RoboticsSim...")
        env_cls = EnvironmentRegistry.load_environment("environments.robotics_sim", "RoboticsSim")
        env = env_cls(joint_count=4)
        self.assertEqual(len(env.joints), 4)
        state_after_step = env.step({"joint_index": 0, "delta": 1.5})
        print(f"RoboticsSim state: {state_after_step}")
        self.assertEqual(state_after_step["joints"][0], 1.5)

if __name__ == "__main__":
    unittest.main()
