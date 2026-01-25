import unittest
import os
import csv
import json
import time
import pandas as pd
from dashboards.data_loader import load_metrics, load_messages, METRICS_FILE, MESSAGE_LOG

class TestDashboardLoad(unittest.TestCase):
    def setUp(self):
        # We don't delete existing, we might simply overwrite for this test
        # Actually safer to create a temp setup or just overwrite
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        
    def test_high_volume_loading(self):
        """
        Benchmarks data loading performance with 100,000 metrics and 10,000 messages.
        Target: < 1.0 second load time for responsive UI.
        """
        ROW_COUNT = 100000
        MSG_COUNT = 10000
        
        print(f"\nGeneraring Load: {ROW_COUNT} metric rows, {MSG_COUNT} messages...")
        
        # 1. Generate Metrics (CSV)
        start_gen = time.time()
        with open(METRICS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "step", "agent_id", "epsilon", "reward"])
            # Batch write for speed
            rows = []
            for i in range(ROW_COUNT):
                rows.append([f"2025-01-01T12:00:{i%60}", i, "Agent-LoadTest", 0.5, float(i)])
            writer.writerows(rows)
        print(f"Metrics Generation Time: {time.time() - start_gen:.4f}s")
        
        # 2. Generate Messages (JSONL)
        start_gen = time.time()
        with open(MESSAGE_LOG, "w") as f:
            for i in range(MSG_COUNT):
                msg = {
                    "timestamp": f"2025-01-01T12:00:{i%60}", 
                    "sender": f"Agent-{i%10}", 
                    "receiver": f"Agent-{i%10+1}", 
                    "trace_id": f"trace_{i//5}", 
                    "topic": "stress_test", 
                    "message_type": "info", 
                    "payload": {"data": "x"*100} # 100 bytes payload
                }
                f.write(json.dumps(msg) + "\n")
        print(f"Messages Generation Time: {time.time() - start_gen:.4f}s")
        
        # 3. Benchmark Metrics Load
        print("Benchmarking Metrics Load...")
        start_load = time.time()
        df_metrics = load_metrics()
        load_time_metrics = time.time() - start_load
        
        print(f"Metrics Load Time: {load_time_metrics:.4f}s (Rows: {len(df_metrics)})")
        self.assertLess(load_time_metrics, 1.0, "Metrics load too slow > 1s")
        
        # 4. Benchmark Messages Load
        print("Benchmarking Messages Load...")
        start_load = time.time()
        msgs = load_messages()
        load_time_msgs = time.time() - start_load
        
        print(f"Messages Load Time: {load_time_msgs:.4f}s (Count: {len(msgs)})")
        
        # Messages might be slower due to JSON parsing. 
        # Streamlit usually caches, but initial load matters.
        # Let's target < 2.0s for 10k messages JSON parse
        self.assertLess(load_time_msgs, 2.0, "Messages load too slow > 2s")
        
        print("PASS: High volume load verified within limits.")

if __name__ == "__main__":
    unittest.main()
