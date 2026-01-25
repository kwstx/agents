import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_registry import AgentRegistry
from environments.env_registry import EnvironmentRegistry
from tests.malformed_plugins import AgentMissingMethod, EnvMissingReset

class TestPluginContract(unittest.TestCase):
    def test_load_malformed_agent(self):
        """
        Ensure loading an agent missing required methods raises TypeError.
        """
        print("\nTesting loading of malformed agent...")
        with self.assertRaises(TypeError) as context:
            # We can't easily dynamic load this file itself without it being in a package structure that importlib likes for dotted paths relative to root or having it in the path.
            # But the registries take a module path.
            # To test the registry logic, we can verify the class validaton logic directly or point to this file.
            # Since 'tests.malformed_plugins' is importable if cwd is root.
            AgentRegistry.load_agent("tests.malformed_plugins", "AgentMissingMethod")
        
        print(f"Caught expected error: {context.exception}")
        error_msg = str(context.exception)
        self.assertTrue("missing required method" in error_msg or "is abstract" in error_msg)

    def test_load_malformed_env(self):
        """
        Ensure loading an environment missing required methods raises TypeError.
        """
        print("\nTesting loading of malformed environment...")
        with self.assertRaises(TypeError) as context:
            EnvironmentRegistry.load_environment("tests.malformed_plugins", "EnvMissingReset")
            
        print(f"Caught expected error: {context.exception}")
        error_msg = str(context.exception)
        self.assertTrue("missing required method" in error_msg or "is abstract" in error_msg)

if __name__ == '__main__':
    unittest.main()
