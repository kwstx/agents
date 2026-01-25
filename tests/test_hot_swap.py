import unittest
import sys
import os
import asyncio
import importlib
import shutil
import time
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.message_bus import MessageBus
from agents.agent_registry import AgentRegistry
from agents.base_agent import BaseAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestHotSwap")

TEMP_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "temp_plugins")
TEMP_AGENT_FILE = os.path.join(TEMP_PLUGIN_DIR, "hot_swap_agent.py")

class TestHotSwap(unittest.TestCase):
    def setUp(self):
        # Create temp directory for dynamic plugins
        os.makedirs(TEMP_PLUGIN_DIR, exist_ok=True)
        # Create __init__.py to make it a package
        with open(os.path.join(TEMP_PLUGIN_DIR, "__init__.py"), "w") as f:
            f.write("")
        
        self.message_bus = MessageBus()
        self.control_agent = None
        self.test_agent = None

    def tearDown(self):
        # Cleanup
        if os.path.exists(TEMP_PLUGIN_DIR):
            shutil.rmtree(TEMP_PLUGIN_DIR)
        
        # Force garbage collection/cleanup if possible, though strict python module unloading is hard
        # We invalid caches to allow future runs
        importlib.invalidate_caches()

    def create_agent_file(self, content):
        with open(TEMP_AGENT_FILE, "w") as f:
            f.write(content)
        # Important: invalidate caches so importlib sees the new file/timestamp
        importlib.invalidate_caches()
        
        # If the module was already loaded, we might need to rely on reload, 
        # but for 'create' we assume it might be new or overwritten.
        
    async def run_isolation_check(self):
        """
        Background task to ensure the control agent keeps receiving messages
        while we mess with the other agent.
        """
        isolated = True
        received_count = 0
        
        async def handler(msg):
            nonlocal received_count
            received_count += 1
            
        self.message_bus.subscribe("control_topic", handler)
        
        # Simulate heartbeat from system
        for _ in range(5):
            await self.message_bus.publish("control_topic", "system", "heartbeat", auth_token=None)
            await asyncio.sleep(0.1)
            
        if received_count < 5:
            isolated = False
            
        return isolated

    def test_hot_swap_workflow(self):
        async def async_test():
            await self.message_bus.start()
            
            # 1. Setup Control Agent (AgentB)
            # We'll just manually register/subscribe to mimic a running agent
            self.message_bus.register("agent_b")
            received_b = []
            self.message_bus.subscribe("topic_b", lambda m: received_b.append(m))

            # 2. Create version 1 of HotSwapAgent
            v1_code = """
from agents.base_agent import BaseAgent
class HotSwapAgent(BaseAgent):
    async def process_task(self, task):
        return "version_1"
"""
            self.create_agent_file(v1_code)
            
            # Load V1
            logger.info("Loading V1...")
            # We import using the path relative to project root, assuming 'tests' is a package or in path
            # Since we added project root to path, 'tests.temp_plugins.hot_swap_agent' should work
            module_name = "tests.temp_plugins.hot_swap_agent"
            
            # First load
            agent_cls_v1 = AgentRegistry.load_agent(module_name, "HotSwapAgent")
            agent_v1 = agent_cls_v1(agent_id="hot_swap_a", message_bus=self.message_bus)
            
            # Verify V1 behavior
            res_v1 = await agent_v1.process_task("test")
            self.assertEqual(res_v1, "version_1")
            
            # Verify Agent B is fine
            await self.message_bus.publish("topic_b", "system", "ping", auth_token=None)
            await asyncio.sleep(0.1)
            self.assertEqual(len(received_b), 1)

            # 3. Unload V1 (Simulate Stop)
            logger.info("Stopping V1...")
            await agent_v1.stop()
            del agent_v1
            del agent_cls_v1
            # In Python, we can't easily 'unload' a module from memory completely, 
            # but we can ensure the runtime state (subscriptions) is clean.
            
            # Verify cleanup: The agent should verify subscriptions are gone in its stop()
            # We can inspect message bus subscribers if we want, but stop() calls unsubscribe.
            
            # 4. Modify to Version 2
            logger.info("Modifying code to V2...")
            v2_code = """
from agents.base_agent import BaseAgent
class HotSwapAgent(BaseAgent):
    async def process_task(self, task):
        return "version_2"
"""
            # Wait a tick to ensure file mtime changes (fast filesystems might be too fast)
            await asyncio.sleep(0.1) 
            self.create_agent_file(v2_code)
            
            # 5. Reload
            logger.info("Reloading V2...")
            # Force reload of the module
            import sys
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            
            # Load again via Registry
            agent_cls_v2 = AgentRegistry.load_agent(module_name, "HotSwapAgent")
            agent_v2 = agent_cls_v2(agent_id="hot_swap_a", message_bus=self.message_bus)
            
            # Verify V2 behavior
            res_v2 = await agent_v2.process_task("test")
            self.assertEqual(res_v2, "version_2")
            
            # 6. Verify Isolation (Agent B still listening)
            await self.message_bus.publish("topic_b", "system", "ping2", auth_token=None)
            await asyncio.sleep(0.1)
            self.assertEqual(len(received_b), 2)
            
            logger.info("Hot-swap success!")
            await self.message_bus.stop()

        asyncio.run(async_test())

if __name__ == '__main__':
    unittest.main()
