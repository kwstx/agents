import unittest
import sys
import os
import asyncio
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from agents.base_agent import BaseAgent

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define malicious agent source code strings to write to temp files
INFINITE_LOOP_AGENT = """
from agents.base_agent import BaseAgent
import asyncio

class InfiniteLoopAgent(BaseAgent):
    async def process_task(self, task):
        while True:
            await asyncio.sleep(0.1)
"""

HACKER_AGENT = """
from agents.base_agent import BaseAgent
import os

class HackerAgent(BaseAgent):
    async def process_task(self, task):
        return os.getcwd()
"""

SUBPROCESS_AGENT = """
from agents.base_agent import BaseAgent
import subprocess

class SubprocessAgent(BaseAgent):
    async def process_task(self, task):
        return "owned"
"""

TEMP_SEC_DIR = os.path.join(os.path.dirname(__file__), "temp_security")

class TestSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(TEMP_SEC_DIR, exist_ok=True)
        with open(os.path.join(TEMP_SEC_DIR, "__init__.py"), "w") as f:
            f.write("")
            
        with open(os.path.join(TEMP_SEC_DIR, "infinite_agent.py"), "w") as f:
            f.write(INFINITE_LOOP_AGENT)
            
        with open(os.path.join(TEMP_SEC_DIR, "hacker_agent.py"), "w") as f:
            f.write(HACKER_AGENT)

        with open(os.path.join(TEMP_SEC_DIR, "subprocess_agent.py"), "w") as f:
            f.write(SUBPROCESS_AGENT)
        
        import importlib
        importlib.invalidate_caches()

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists(TEMP_SEC_DIR):
            shutil.rmtree(TEMP_SEC_DIR)

    async def _timeout_protection_async(self):
        print("\nTesting Execution Timeout...")
        from tests.temp_security.infinite_agent import InfiniteLoopAgent
        
        agent_cls = AgentRegistry.load_agent("tests.temp_security.infinite_agent", "InfiniteLoopAgent")
        
        class MockBus:
            def register(self, aid): return "token"
            def subscribe(self, t, h): pass
            
        agent = agent_cls("loop_bot", message_bus=MockBus())
        
        # Mock memory setup to avoid DB creation
        async def mock_setup(): pass
        agent.setup_memory = mock_setup
        
        # Start the agent loop
        await agent.start()
        
        # Add a task that will freeze
        task_payload = "freeze"
        await agent.add_task(task_payload)
        
        print("Waiting 6 seconds for timeout handling...")
        await asyncio.sleep(6)
        
        await agent.stop()
        
        # Verify result via checkpoint
        # Checkpoint dir: logs/checkpoints/loop_bot
        checkpoint_dir = os.path.join("logs", "checkpoints", "loop_bot")
        self.assertTrue(os.path.exists(checkpoint_dir), "Checkpoint directory not created")
        
        # Find latest json
        files = os.listdir(checkpoint_dir)
        files.sort()
        latest = files[-1]
        
        import json
        with open(os.path.join(checkpoint_dir, latest), "r") as f:
            data = json.load(f)
            
        print(f"Checkpoint data: {data}")
        # result string might be stringified dict
        result_str = data.get("result")
        # It might be a string representation of a dict or None
        self.assertIn("Execution Timed Out", str(result_str))

    def test_timeout_protection(self):
        asyncio.run(self._timeout_protection_async())
        print("Timeout protection verified.")

    def test_import_blocking_os(self):
        print("\nTesting dangerous import blocking (os)...")
        with self.assertRaises(ImportError) as context:
            AgentRegistry.load_agent("tests.temp_security.hacker_agent", "HackerAgent")
            
        print(f"Caught expected security error: {context.exception}")
        self.assertIn("Security Alert", str(context.exception))
        self.assertIn("os", str(context.exception))

    def test_import_blocking_subprocess(self):
        print("\nTesting dangerous import blocking (subprocess)...")
        with self.assertRaises(ImportError) as context:
            AgentRegistry.load_agent("tests.temp_security.subprocess_agent", "SubprocessAgent")
        
        print(f"Caught expected security error: {context.exception}")
        self.assertIn("Security Alert", str(context.exception))
        self.assertIn("subprocess", str(context.exception))

if __name__ == '__main__':
    unittest.main()
