import unittest
import os
import json
import time
import subprocess
import pandas as pd
from datetime import datetime

# Paths
CONTROL_FILE = "control.json"
EVENT_LOG = "logs/simulation_events.jsonl"
METRICS_FILE = "logs/learning_metrics.csv"

class TestReversibility(unittest.TestCase):
    def setUp(self):
        # Clean Start
        with open(CONTROL_FILE, "w") as f:
            json.dump({
                "status": "STOPPED", 
                "stress_config": {"latency_range": [0,0], "failure_rate": 0},
                "agent_params": {"epsilon": 1.0}
            }, f)
        
        if os.path.exists(EVENT_LOG):
            os.remove(EVENT_LOG)
        if os.path.exists(METRICS_FILE):
            os.remove(METRICS_FILE)

    def _count_events(self, event_type="ERROR"):
        if not os.path.exists(EVENT_LOG):
            return 0
        count = 0
        with open(EVENT_LOG, "r") as f:
            for line in f:
                try:
                    if json.loads(line).get("type") == event_type:
                        count += 1
                except:
                    pass
        return count

    def test_stress_recovery(self):
        print("\nStarting Simulation Runner...")
        process = subprocess.Popen(
            ["python", "simulation_runner.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # 1. Baseline: Start Healthy
            print("Phase 1: Healthy Start")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "RUNNING"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            
            time.sleep(3)
            # Should be 0 errors
            self.assertEqual(self._count_events(), 0, "Baseline should have no errors")
            
            # 2. Inject Massive Failure
            print("Phase 2: Inject Faults (100% Failure)")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["stress_config"]["failure_rate"] = 1.0
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(3)
            errors_during_stress = self._count_events()
            print(f"Errors during stress: {errors_during_stress}")
            self.assertGreater(errors_during_stress, 0, "Should have logged errors during stress")
            
            # 3. Recover: Clear Faults
            print("Phase 3: Recovery")
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["stress_config"]["failure_rate"] = 0.0
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            time.sleep(3)
            
            # 4. Verify Clean State
            # Count errors again. Should be same as phase 2 (no NEW errors)
            errors_after_recovery = self._count_events()
            new_errors = errors_after_recovery - errors_during_stress
            
            # Allow at most 1 race-condition error from the exact moment of switch
            self.assertLessEqual(new_errors, 1, f"System kept failing after recovery! New errors: {new_errors}")
            
            print("PASS: System recovered cleanly. No residual failures.")
            
        finally:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    unittest.main()
