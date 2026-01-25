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

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists(TEMP_SEC_DIR):
            shutil.rmtree(TEMP_SEC_DIR)

    def test_timeout_protection(self):
        print("\nTesting Execution Timeout...")
        async def run_timeout():
             from tests.temp_security.infinite_agent import InfiniteLoopAgent
             # Loading this one is safe (imports are fine)
             
             # Note: AgentRegistry can load it fine
             agent_cls = AgentRegistry.load_agent("tests.temp_security.infinite_agent", "InfiniteLoopAgent")
             
             class MockBus:
                def register(self, aid): return "token"
                def subscribe(self, t, h): pass
                
             agent = agent_cls("loop_bot", message_bus=MockBus())
             
             # Override timeout to be fast for test
             # BaseAgent timeout is hardcoded to 5.0 currently in the replacement chunk I sent.
             # Wait, I hardcoded 5.0. Ideally it should be configurable. 
             # I can patch wait_for? No, too complex.
             # 5 seconds is acceptable for a test run.
             
             print("Please wait 5 seconds for timeout...")
             result = await agent.process_task("freeze")
             
             # agent catches timeout and returns error dict
             self.assertEqual(result.get("status"), "failed")
             self.assertEqual(result.get("error"), "Execution Timed Out")
             
        asyncio.run(run_timeout())
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
