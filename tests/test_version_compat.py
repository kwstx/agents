import unittest
import sys
import os
import asyncio
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry

class MockMessageBus:
    def register(self, agent_id): return "token"
    def subscribe(self, topic, handler): pass

class TestVersionCompat(unittest.TestCase):
    def setUp(self):
        self.mock_bus = MockMessageBus()

    def test_legacy_v1_loading(self):
        """
        Verify V1 (legacy) agent loads and works via compatibility shim.
        """
        print("\nTesting Legacy V1 Agent Loading...")
        agent_cls = AgentRegistry.load_agent("tests.versions.agent_v1_legacy", "AgentV1Legacy")
        agent = agent_cls(agent_id="legacy_bot", message_bus=self.mock_bus)
        
        # Verify it works
        result = asyncio.run(agent.process_task("test_legacy"))
        print(f"Legacy result: {result}")
        self.assertEqual(result, "v1_legacy_result: test_legacy")
        
        # We can't easily assert on logs here without capturing handlers, 
        # but manual inspection or advanced log capturing would verify the warning.

    def test_modern_v2_loading(self):
        """
        Verify V2 (modern) agent loads and works normally.
        """
        print("\nTesting Modern V2 Agent Loading...")
        agent_cls = AgentRegistry.load_agent("tests.versions.agent_v2_modern", "AgentV2Modern")
        agent = agent_cls(agent_id="modern_bot", message_bus=self.mock_bus)
        
        result = asyncio.run(agent.process_task("test_modern"))
        print(f"Modern result: {result}")
        self.assertEqual(result, "v2_modern_result: test_modern")

if __name__ == '__main__':
    unittest.main()
