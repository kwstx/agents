import unittest
import sys
import os
import asyncio
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from utils.message_bus import MessageBus
from environments.env_registry import EnvironmentRegistry

# Configure logging to capture output
logging.basicConfig(level=logging.INFO)

class TestVerticalIsolation(unittest.TestCase):
    def setUp(self):
        self.message_bus = MessageBus()

    class CrashingAgent(AgentRegistry.load_agent("agents.finance_agent", "FinanceAgent")):
        """
        A mock agent that we inject to simulate a crash.
        We subclass FinanceAgent because BaseAgent is abstract and cannot be loaded by registry.
        """
        async def process_task(self, task):
            if task == "die":
                raise RuntimeError("Vertical Agent Crash!")
            return "processed"

    def test_finance_agent_isolation(self):
        """
        Verify FinanceAgent runs and doesn't crash on normal tasks.
        """
        print("\nTesting FinanceAgent normal execution...")
        agent_cls = AgentRegistry.load_agent("agents.finance_agent", "FinanceAgent")
        agent = agent_cls("fin_agent", message_bus=self.message_bus)
        
        res = asyncio.run(agent.process_task({"type": "market_update", "data": {"sentiment": "bullish"}}))
        self.assertEqual(res["action"], "buy")
        print("FinanceAgent passed normal execution.")

    def test_error_containment(self):
        """
        Verify that if one agent crashes, the system/control agent survives.
        """
        print("\nTesting Error Containment...")
        
        # 1. Setup Control Agent (just a listener)
        received_msgs = []
        self.message_bus.register("control")
        self.message_bus.subscribe("control_topic", lambda m: received_msgs.append(m))
        
        # 2. Setup Crashing Agent
        # We inject a bad agent. In a real scenario, this would be a loaded module.
        # For this test, we accept we are simulating the behavior of the *runtime* handling the crash.
        # But wait, BaseAgent._process_tasks wraps execution in try/except!
        # So we verify that the try/except block works as intended.
        
        agent_cls = AgentRegistry.load_agent("agents.finance_agent", "FinanceAgent")
        
        # We monkeypatch the process_task of the INSTANCE to crash
        agent = agent_cls("crasher", message_bus=self.message_bus)
        
        async def crashing_process(task):
            raise RuntimeError("POISON PILL")
            
        agent.process_task = crashing_process
        
        async def run_scenario():
            await self.message_bus.start() # Ensure bus is running
            await agent.start()
            
            # Send a task that will crash it
            await agent.add_task("bad_task")
            
            # Allow time for processing
            await asyncio.sleep(0.1)
            
            # Verify agent is still 'running' but logged an error (didn't exit process)
            # BaseAgent catches exceptions in _process_tasks
            self.assertTrue(agent.running, "Agent should still be in running loop state despite error")
            
            # Verify Control Agent still gets messages
            await self.message_bus.publish("control_topic", "system", "ping", auth_token=None)
            await asyncio.sleep(0.1)
            self.assertEqual(len(received_msgs), 1)
            
            await agent.stop()
            
        asyncio.run(run_scenario())
        print("Error Containment passed: Agent crashed on task but runtime survived.")

if __name__ == '__main__':
    unittest.main()
