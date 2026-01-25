import unittest
import os
import json
import time
import subprocess
import pandas as pd
from datetime import datetime

# Paths
CONTROL_FILE = "control.json"
METRICS_FILE = "logs/learning_metrics.csv"

class TestInteractiveControls(unittest.TestCase):
    def setUp(self):
        # Reset control file
        with open(CONTROL_FILE, "w") as f:
            json.dump({
                "status": "STOPPED", 
                "stress_config": {"latency_range": [0,0], "failure_rate": 0},
                "agent_params": {"epsilon": 1.0}
            }, f)
            
        if os.path.exists(METRICS_FILE):
            os.remove(METRICS_FILE)

    def _get_metric_count(self):
        if not os.path.exists(METRICS_FILE):
            return 0
        try:
            # Simple line count is faster/safer for checking updates
            with open(METRICS_FILE, "r") as f:
                return sum(1 for line in f)
        except:
            return 0
            
    def _get_last_epsilon(self):
        if not os.path.exists(METRICS_FILE):
            return None
        try:
            df = pd.read_csv(METRICS_FILE)
            if not df.empty:
                return df.iloc[-1]["epsilon"]
        except:
            pass
        return None

    def test_controls(self):
        print("\nStarting Simulation Runner...")
        process = subprocess.Popen(
            ["python", "simulation_runner.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # 1. Start
            print("Action: START")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "RUNNING"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            
            time.sleep(3)
            count_running = self._get_metric_count()
            self.assertGreater(count_running, 1, "Simulation should be producing logs")
            
            # 2. Pause
            print("Action: PAUSE")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "PAUSED"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(2)
            count_paused = self._get_metric_count()
            
            # Allow at most 1 extra log due to race/in-flight step
            self.assertLessEqual(count_paused - count_running, 1, "Simulation should stop logging when paused")
            print(f"Logs during pause: {count_paused - count_running}")
            
            # 3. Modify Parameter (Epsilon)
            print("Action: MODIFY PARAM (Epsilon -> 0.123)")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["agent_params"]["epsilon"] = 0.123
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            # 4. Resume
            print("Action: RESUME")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "RUNNING"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(3)
            count_resumed = self._get_metric_count()
            self.assertGreater(count_resumed, count_paused, "Simulation should resume logging")
            
            # 5. Verify Parameter Update
            last_eps = self._get_last_epsilon()
            self.assertAlmostEqual(last_eps, 0.123, places=3, msg="Agent should have picked up new epsilon value")
            print(f"Verified Epsilon: {last_eps}")
            
        finally:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    unittest.main()
