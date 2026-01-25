import unittest
import sys
import os
# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shutil
import importlib
from agents.agent_registry import AgentRegistry

# Define directory for temp dependency tests
TEMP_DEPS_DIR = os.path.join(os.path.dirname(__file__), "temp_deps")

# Simple agent code
SIMPLE_AGENT = """
from agents.base_agent import BaseAgent
import asyncio

class ConflictAgent(BaseAgent):
    async def process_task(self, task):
        return "ok"
"""

class TestDependencyConflicts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(TEMP_DEPS_DIR, exist_ok=True)
        with open(os.path.join(TEMP_DEPS_DIR, "__init__.py"), "w") as f:
            f.write("")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_DEPS_DIR):
            shutil.rmtree(TEMP_DEPS_DIR)

    def setUp(self):
        # Create a fresh agent directory for each test usually, 
        # but we can just use different subdirs or overwrite.
        self.agent_dir = os.path.join(TEMP_DEPS_DIR, "conflict_agent")
        os.makedirs(self.agent_dir, exist_ok=True)
        with open(os.path.join(self.agent_dir, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(self.agent_dir, "agent.py"), "w") as f:
            f.write(SIMPLE_AGENT)

    def test_missing_dependency(self):
        # Create manifest with non-existent package
        manifest = """
dependencies:
  non_existent_package_12345: "==1.0.0"
"""
        with open(os.path.join(self.agent_dir, "manifest.yaml"), "w") as f:
            f.write(manifest)
            
        print("\nTesting Missing Dependency...")
        with self.assertRaises(ImportError) as context:
            AgentRegistry.load_agent("tests.temp_deps.conflict_agent.agent", "ConflictAgent")
            
        print(f"Caught expected error: {context.exception}")
        self.assertIn("Missing Dependency", str(context.exception))
        self.assertIn("non_existent_package_12345", str(context.exception))

    def test_version_conflict(self):
        # We need to pick a package that IS installed but ask for wrong version.
        # We'll use 'packaging' since we imported it in registry, so it must be there.
        # Check current version first ideally, but usually asking for "==0.0.1" is safe fail.
        
        manifest = """
dependencies:
  packaging: "==0.0.1"
"""
        with open(os.path.join(self.agent_dir, "manifest.yaml"), "w") as f:
            f.write(manifest)
            
        print("\nTesting Version Conflict...")
        with self.assertRaises(ImportError) as context:
            AgentRegistry.load_agent("tests.temp_deps.conflict_agent.agent", "ConflictAgent")
            
        print(f"Caught expected error: {context.exception}")
        self.assertIn("Dependency Conflict", str(context.exception))
        self.assertIn("packaging==0.0.1", str(context.exception))

    def test_valid_dependency(self):
        # Ask for Any version of packaging or a very broad range
        manifest = """
dependencies:
  packaging: ">=0.1"
"""
        with open(os.path.join(self.agent_dir, "manifest.yaml"), "w") as f:
            f.write(manifest)
            
        print("\nTesting Valid Dependency...")
        try:
            agent_cls = AgentRegistry.load_agent("tests.temp_deps.conflict_agent.agent", "ConflictAgent")
            self.assertIsNotNone(agent_cls)
            print("Successfully loaded agent with valid dependency.")
        except ImportError as e:
            self.fail(f"Should not have raised ImportError: {e}")

if __name__ == '__main__':
    unittest.main()
