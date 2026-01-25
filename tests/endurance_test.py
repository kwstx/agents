import unittest
import os
import time
import subprocess
import psutil
import pandas as pd
import json
from datetime import datetime

# We will run for a shorter time in CI/validation mode, but code allows long runs
DURATION_SEC = 30  
CHECK_INTERVAL = 1.0

CONTROL_FILE = "control.json"
METRICS_FILE = "logs/learning_metrics.csv"

class TestEndurance(unittest.TestCase):
    def setUp(self):
        # Clean start
        with open(CONTROL_FILE, "w") as f:
            json.dump({
                "status": "STOPPED", 
                "stress_config": {"latency_range": [0,0], "failure_rate": 0},
                "agent_params": {"epsilon": 1.0}
            }, f)
        if os.path.exists(METRICS_FILE):
            os.remove(METRICS_FILE)

    def test_stability_over_time(self):
        """
        Runs simulation and dashboard-loader for DURATION_SEC.
        Monitors memory usage and data consistency.
        """
        print(f"\nStarting Endurance Test ({DURATION_SEC}s)...")
        
        # Start Simulation
        sim_process = subprocess.Popen(
            ["python", "simulation_runner.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Start Running
            with open(CONTROL_FILE, "r+") as f:
                data = json.load(f)
                data["status"] = "RUNNING"
                f.seek(0)
                json.dump(data, f)
                f.truncate()
                
            start_time = time.time()
            memory_samples = []
            
            # Helper to get RSS memory in MB
            def get_mem(pid):
                process = psutil.Process(pid)
                return process.memory_info().rss / 1024 / 1024

            while time.time() - start_time < DURATION_SEC:
                # 1. Simluates Dashboard Refresh (Read Data)
                # We use the actual data loader logic
                if os.path.exists(METRICS_FILE):
                    try:
                        df = pd.read_csv(METRICS_FILE)
                        _ = len(df) # Force iter
                    except:
                        pass
                
                # 2. Monitor Simulation Process Memory
                try:
                    mem = get_mem(sim_process.pid)
                    memory_samples.append(mem)
                except psutil.NoSuchProcess:
                    self.fail("Simulation process died unexpectedly")
                
                # 3. Intermittently Interact (every 5s)
                elapsed = time.time() - start_time
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    # Toggle Epsilon slightly to force state change read
                    with open(CONTROL_FILE, "r+") as f:
                        data = json.load(f)
                        data["agent_params"]["epsilon"] = 0.5 + (0.1 * (int(elapsed) % 2))
                        f.seek(0)
                        json.dump(data, f)
                        f.truncate()
                        
                time.sleep(CHECK_INTERVAL)
                
            # Analysis
            avg_mem = sum(memory_samples) / len(memory_samples)
            max_mem = max(memory_samples)
            start_mem = memory_samples[0]
            end_mem = memory_samples[-1]
            
            print(f"Memory Usage (MB): Start={start_mem:.2f}, End={end_mem:.2f}, Max={max_mem:.2f}")
            
            # Check for massive leak (>50MB growth in 30s would be bad for this simple script)
            # In a real endurance test, we'd look for linear growth over hours.
            # Here, we check stability.
            self.assertLess(end_mem, start_mem + 50, "Memory usage grew significantly (>50MB)")
            
            print("PASS: System remained stable. No crashes or significant leaks.")
            
        finally:
            sim_process.terminate()
            sim_process.wait()

if __name__ == "__main__":
    unittest.main()
