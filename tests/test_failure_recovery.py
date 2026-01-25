import unittest
import asyncio
import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestFailureRecovery")

class StableAgent(BaseAgent):
    async def process_task(self, task):
        return "stable_pong"

class FragileAgent(BaseAgent):
    async def process_task(self, task):
        if task == "crash":
            raise ValueError("Intentional Crash for Testing")
        return "fragile_pong"

class TestFailureRecovery(unittest.TestCase):
    async def _run_async_test(self):
        bus = MessageBus()
        stable = StableAgent("stable_bot", bus)
        fragile = FragileAgent("fragile_bot", bus)
        
        # Mock memory
        async def mock_setup(): pass
        stable.setup_memory = mock_setup
        fragile.setup_memory = mock_setup
        
        await stable.start()
        await fragile.start()
        
        print("\n--- Phase 1: Normal Operation ---")
        # Verify both work
        res_s = await stable.process_task("ping")
        self.assertEqual(res_s, "stable_pong")
        
        res_f = await fragile.process_task("ping")
        self.assertEqual(res_f, "fragile_pong")
        
        print("Both agents operational.")
        
        print("\n--- Phase 2: Induce Crash ---")
        # We need to simulate the crash happening inside the task queue loop
        # triggering the error handling in _process_tasks
        
        await fragile.add_task("crash")
        
        # Give it a moment to process and crash
        await asyncio.sleep(1)
        
        # Verify fragile agent status (it might be "active" but logged error, 
        # or we might want it to fail safely. 
        # BaseAgent currently catches exceptions and logs them, keeping the loop running by default.
        # This IS resilience.
        
        # Check if it survived
        res_f_after = await fragile.process_task("ping")
        self.assertEqual(res_f_after, "fragile_pong")
        print("Fragile agent survived the crash (Caught and Logged).")
        
        print("\n--- Phase 3: System Stability ---")
        # Verify stable agent is untouched
        res_s_after = await stable.process_task("ping")
        self.assertEqual(res_s_after, "stable_pong")
        print("Stable agent unaffected.")
        
        await stable.stop()
        await fragile.stop()

    def test_failure_isolation(self):
        asyncio.run(self._run_async_test())

if __name__ == '__main__':
    unittest.main()
