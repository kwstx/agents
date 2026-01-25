import unittest
import os
import csv
import pandas as pd
import shutil
from dashboards.data_loader import load_metrics, METRICS_FILE

class TestLearningCurveAccuracy(unittest.TestCase):
    def setUp(self):
        # Backup existing metrics
        if os.path.exists(METRICS_FILE):
            shutil.move(METRICS_FILE, METRICS_FILE + ".bak")
            
        # Ensure dir exists
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)

    def tearDown(self):
        # Restore backup
        if os.path.exists(METRICS_FILE):
            os.remove(METRICS_FILE)
        if os.path.exists(METRICS_FILE + ".bak"):
            shutil.move(METRICS_FILE + ".bak", METRICS_FILE)

    def test_metric_fidelity(self):
        """
        Verify that learning metrics (Rewards, Loss, Epsilon) are loaded 
        exactly as logged, preventing visualization artifacts.
        """
        # 1. Define Ground Truth Training Data
        # Simulating a clear learning trend: Reward increases, Epsilon decreases
        ground_truth = [
            {"timestamp": "2025-01-01T12:00:00", "step": 0, "agent_id": "A1", "epsilon": 1.0, "reward": -1.0},
            {"timestamp": "2025-01-01T12:00:01", "step": 1, "agent_id": "A1", "epsilon": 0.99, "reward": -0.5},
            {"timestamp": "2025-01-01T12:00:02", "step": 2, "agent_id": "A1", "epsilon": 0.98, "reward": 0.0},
            {"timestamp": "2025-01-01T12:00:03", "step": 3, "agent_id": "A1", "epsilon": 0.95, "reward": 2.5}, # Spike
            {"timestamp": "2025-01-01T12:00:04", "step": 4, "agent_id": "A1", "epsilon": 0.90, "reward": 5.0},
        ]
        
        # 2. Write to Log
        with open(METRICS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "step", "agent_id", "epsilon", "reward"])
            for row in ground_truth:
                writer.writerow([row["timestamp"], row["step"], row["agent_id"], row["epsilon"], row["reward"]])
                
        # 3. Load via Dashboard Pipeline
        df = load_metrics()
        
        # 4. Verify Accuracy
        self.assertFalse(df.empty, "Dataframe should not be empty")
        self.assertEqual(len(df), 5, "Should have 5 records")
        
        # Check specific values (Float precision is critical for Loss/Epsilon)
        # Pandas allows some float tolerance, but we expect exact values for these simple floats
        self.assertEqual(df.iloc[0]["epsilon"], 1.0)
        self.assertEqual(df.iloc[4]["epsilon"], 0.90)
        
        self.assertEqual(df.iloc[0]["reward"], -1.0)
        self.assertEqual(df.iloc[3]["reward"], 2.5)
        self.assertEqual(df.iloc[4]["reward"], 5.0)
        
        # Check Step sequence implies integrity
        pd.testing.assert_series_equal(df["step"], pd.Series([0, 1, 2, 3, 4], name="step"))
        
        print("PASS: Learning metrics preserved with exact fidelity.")

if __name__ == "__main__":
    unittest.main()
