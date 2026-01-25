import unittest
import os
import json
import pandas as pd
import shutil
from dashboards.data_loader import (
    load_control, save_control, load_metrics, load_events, 
    get_available_agents, get_agent_checkpoints, load_checkpoint,
    METRICS_FILE, EVENT_LOG, CONTROL_FILE, LOG_DIR
)

class TestDashboardIntegrity(unittest.TestCase):
    def setUp(self):
        # Backup existing files if they exist
        self.backups = {}
        for f in [METRICS_FILE, EVENT_LOG, CONTROL_FILE]:
            if os.path.exists(f):
                shutil.move(f, f + ".bak")
                self.backups[f] = True
        
        # Ensure log dir exists
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

    def tearDown(self):
        # Restore backups
        for f in [METRICS_FILE, EVENT_LOG, CONTROL_FILE]:
            if os.path.exists(f):
                os.remove(f)
            if self.backups.get(f):
                shutil.move(f + ".bak", f)
                
        # Cleanup dummy agent
        dummy_agent_dir = os.path.join(LOG_DIR, "test_agent")
        if os.path.exists(dummy_agent_dir):
            shutil.rmtree(dummy_agent_dir)

    def test_metrics_integrity(self):
        """Test that learning metrics are read from the single source of truth."""
        # 1. Write Truth
        truth_data = "timestamp,step,agent_id,epsilon,reward\n2025-01-01T12:00:00,1,agent_1,0.9,10.5\n2025-01-01T12:01:00,2,agent_1,0.8,15.0"
        with open(METRICS_FILE, "w") as f:
            f.write(truth_data)
            
        # 2. Read
        df = load_metrics()
        
        # 3. Verify
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["reward"], 10.5)
        self.assertEqual(df.iloc[1]["epsilon"], 0.8)
        print("PASS: Metrics integrity verified.")

    def test_control_mutation(self):
        """Test that control file mutations are reflected."""
        # 1. Write Initial
        initial = {"status": "STOPPED", "agent_params": {"epsilon": 1.0}}
        with open(CONTROL_FILE, "w") as f:
            json.dump(initial, f)
            
        # 2. Read & Verify
        loaded = load_control()
        self.assertEqual(loaded["status"], "STOPPED")
        
        # 3. Mutate (Simulate Dashboard Action)
        loaded["status"] = "RUNNING"
        save_control(loaded)
        
        # 4. Verify Persistence
        with open(CONTROL_FILE, "r") as f:
            persisted = json.load(f)
        self.assertEqual(persisted["status"], "RUNNING")
        print("PASS: Control file mutation verified.")

    def test_event_log_integrity(self):
        """Test event log reading."""
        # 1. Write Truth
        events = [
            {"timestamp": "2025-01-01", "type": "INFO", "msg": "Started"},
            {"timestamp": "2025-01-01", "type": "ERROR", "msg": "Failed"}
        ]
        with open(EVENT_LOG, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
                
        # 2. Read
        loaded_events = load_events()
        
        # 3. Verify
        self.assertEqual(len(loaded_events), 2)
        self.assertEqual(loaded_events[1]["type"], "ERROR")
        print("PASS: Event log integrity verified.")
        
    def test_checkpoint_integrity(self):
        """Test checkpoint detection and reading."""
        # 1. Setup Dummy Agent
        agent_id = "test_agent"
        agent_dir = os.path.join(LOG_DIR, agent_id)
        os.makedirs(agent_dir, exist_ok=True)
        
        checkpoint_file = os.path.join(agent_dir, "step_100.json")
        truth_data = {"step": 100, "state": [0,0]}
        with open(checkpoint_file, "w") as f:
            json.dump(truth_data, f)
            
        # 2. Verify Discovery
        agents = get_available_agents()
        self.assertIn(agent_id, agents)
        
        checkpoints = get_agent_checkpoints(agent_id)
        self.assertEqual(len(checkpoints), 1)
        
        # 3. Verify Content
        data = load_checkpoint(checkpoints[0])
        self.assertEqual(data["step"], 100)
        print("PASS: Checkpoint integrity verified.")

if __name__ == "__main__":
    unittest.main()
