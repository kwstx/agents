import unittest
import os
import json
import time
import subprocess
import threading
from datetime import datetime

# Paths
CONTROL_FILE = "control.json"
EVENT_LOG = "logs/simulation_events.jsonl"
METRICS_FILE = "logs/learning_metrics.csv"

class TestStressVisuals(unittest.TestCase):
    def setUp(self):
        # Reset files
        with open(CONTROL_FILE, "w") as f:
            json.dump({
                "status": "STOPPED", 
                "stress_config": {"latency_range": [0,0], "failure_rate": 0},
                "agent_params": {"epsilon": 0.1}
            }, f)
            
        if os.path.exists(EVENT_LOG):
            os.remove(EVENT_LOG)
        if os.path.exists(METRICS_FILE):
            os.remove(METRICS_FILE)

    def test_stress_injection(self):
        """
        End-to-end test:
        1. Start Simulation (Runner).
        2. Inject Failure Rate via Control File (Dashboard action).
        3. Verify 'ERROR' events appear in log (Dashboard visual).
        """
        print("\nStarting Simulation Runner...")
        # Start runner as subprocess
        process = subprocess.Popen(
            ["python", "simulation_runner.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # 1. Start simulation
            time.sleep(2) # Init time
            print("Activating Simulation...")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "RUNNING"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(2)
            
            # 2. Inject High Failure Rate
            print("Injecting Failures...")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["stress_config"]["failure_rate"] = 0.8 # 80% fail chance
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(3) # Let it run and fail
            
            # 3. Verify Logs
            print("Verifying Logs...")
            errors_found = 0
            if os.path.exists(EVENT_LOG):
                with open(EVENT_LOG, "r") as f:
                    for line in f:
                        event = json.loads(line)
                        if event["type"] == "ERROR" and event["msg"] == "Simulated Failure":
                            errors_found += 1
            
            print(f"Errors Found: {errors_found}")
            self.assertGreater(errors_found, 0, "Should have logged simulated failures")
            
            # 4. Turn off stress
            print("Disabling Stress...")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["stress_config"]["failure_rate"] = 0.0
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(2)
            
            # Count errors again (should not increase much)
            errors_before = errors_found
            if os.path.exists(EVENT_LOG):
                with open(EVENT_LOG, "r") as f:
                    lines = f.readlines()
                    errors_after = sum(1 for line in lines if "Simulated Failure" in line)
            
            # In a perfectly synched world, this is identical. In async 2s window, maybe +1.
            # But rate should be essentially zero.
            print(f"Errors After Reset: {errors_after}")
            
        finally:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    unittest.main()
