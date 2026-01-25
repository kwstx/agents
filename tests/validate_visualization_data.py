import unittest
import os
import json
import shutil
from dashboards.data_loader import load_checkpoint, get_agent_checkpoints

LOG_DIR = "logs/checkpoints"

class TestVisualizationData(unittest.TestCase):
    def setUp(self):
        self.agent_id = "viz_test_agent"
        self.agent_dir = os.path.join(LOG_DIR, self.agent_id)
        os.makedirs(self.agent_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.agent_dir):
            shutil.rmtree(self.agent_dir)

    def test_complex_state_rendering(self):
        """
        Verify that complex nested state structures used for visualization
        are preserved exactly when loaded.
        """
        # 1. Inject Complex State
        complex_state = {
            "position": {"x": 5, "y": 5},
            "inventory": ["item_a", "item_b"],
            "memory": [
                {"role": "user", "content": "Find the goal"},
                {"role": "assistant", "content": "Moving UP"}
            ],
            "internal_vars": {
                "confidence": 0.85,
                "strategy_tree": {
                    "root": "search",
                    "nodes": ["explore", "exploit"]
                }
            }
        }
        
        checkpoint_data = {
            "timestamp": "2025-01-01T12:00:00",
            "agent_id": self.agent_id,
            "task": "Test Visualization",
            "state": complex_state,
            "result": "Pending"
        }
        
        file_path = os.path.join(self.agent_dir, "step_complextest.json")
        with open(file_path, "w") as f:
            json.dump(checkpoint_data, f)
            
        # 2. Load via Dashboard Logic
        # We simulate what the Dashboard does: identify file -> load
        checkpoints = get_agent_checkpoints(self.agent_id)
        self.assertIn(file_path, checkpoints)
        
        loaded_data = load_checkpoint(file_path)
        
        # 3. Verify Equality (Deep Check)
        self.assertEqual(loaded_data["state"]["position"]["x"], 5)
        self.assertEqual(len(loaded_data["state"]["memory"]), 2)
        self.assertEqual(loaded_data["state"]["memory"][0]["content"], "Find the goal")
        self.assertEqual(loaded_data["state"]["internal_vars"]["strategy_tree"]["root"], "search")
        
        print("PASS: Complex state structure verified.")

if __name__ == "__main__":
    unittest.main()
