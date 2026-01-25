import pytest
import json
import os
import tempfile
from datetime import datetime

# Logic extracted from app.py (simulated)
def load_data(log_path):
    data = []
    if not os.path.exists(log_path):
        return data
    with open(log_path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return data

def test_dashboard_data_integrity():
    """Verify dashbaord can parse logs accurately."""
    
    # 1. Create Dummy Log
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        log_path = f.name
        
        # Write valid messages
        msg1 = {"trace_id": "t1", "payload": "p1", "timestamp": "2024-01-01T12:00:00"}
        msg2 = {"trace_id": "t2", "payload": "p2", "timestamp": "2024-01-01T12:00:01"}
        
        f.write(json.dumps(msg1) + "\n")
        f.write(json.dumps(msg2) + "\n")
        # Write garbage line
        f.write("GARBAGE_JSON\n")
        
    try:
        # 2. Run Load Logic
        data = load_data(log_path)
        
        # 3. Verify
        assert len(data) == 2, "Should ignore garbage and load valid lines"
        assert data[0]["trace_id"] == "t1"
        assert data[1]["trace_id"] == "t2"
        
    finally:
        if os.path.exists(log_path):
            os.remove(log_path)
            
    print("Dashboard Data Integrity Verified.")

if __name__ == "__main__":
    test_dashboard_data_integrity()
