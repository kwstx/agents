import pytest
import os
import time
import sqlite3
import random
import json
from datetime import datetime, timedelta
from utils.memory import Memory

DB_PATH = "tests/data/test_endurance.db"
NUM_RECORDS = 100000

def test_memory_endurance():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    mem = Memory(DB_PATH)
    
    print(f"\n--- ENDURANCE TEST: {NUM_RECORDS} Records ---")
    
    # 1. Bulk Injection (Simulate long uptime)
    start_time = time.time()
    mem.conn.execute("BEGIN TRANSACTION;")
    query = "INSERT INTO memories (agent_id, type, content, timestamp, sim_context) VALUES (?, ?, ?, ?, ?)"
    
    # Generate data spanning 30 days
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(NUM_RECORDS):
        # Time progresses linearly
        ts = (base_time + timedelta(seconds=i * 25)).isoformat() # roughly 1 log every 25s
        
        aid = "Agent_LongRunner"
        typ = random.choice(["action", "observation", "thought"])
        content = f"\"Log entry number {i} simulating routine operation\""
        
        ctx = json.dumps({"battery": 100 - (i % 100), "day": i // 3000})
        
        mem.conn.execute(query, (aid, typ, content, ts, ctx))
        
    mem.conn.execute("COMMIT;")
    duration = time.time() - start_time
    print(f"Injection Time: {duration:.2f}s ({(NUM_RECORDS/duration):.0f} records/sec)")
    
    # 2. Disk Usage
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"Database Size: {db_size:.2f} MB")
    
    # 3. Query Performance (Simulate Agent 'Recall Loop')
    # Fetch recent 50
    start_read = time.time()
    recent = mem.get_recent("Agent_LongRunner", limit=50)
    read_duration = time.time() - start_read
    
    print(f"Ready Latency (Last 50): {read_duration:.4f}s")
    assert read_duration < 0.05, "Query degraded! Should be < 50ms even with 100k records."
    assert len(recent) == 50
    
    # 4. Summarization Performance
    start_sum = time.time()
    summary = mem.summarize_context("Agent_LongRunner", limit=100)
    sum_duration = time.time() - start_sum
    
    print(f"Summarization Latency (Last 100): {sum_duration:.4f}s")
    assert sum_duration < 0.1, "Summarization degraded! Should be < 100ms."
    
    # 5. Correctness Check at Tail
    # The last inserted record should be ID ~100000 (autoincrement)
    # and match our loop logic
    last_log = recent[0] # recent is reversed time? get_recent calls query_memory which returns DESC (newest first)
    # So recent[0] is the NEWEST
    
    assert "Log entry number 99999" in str(last_log["content"])
    
    mem.close()
    print("SUCCESS: System remained stable and fast under load.")

if __name__ == "__main__":
    test_memory_endurance()
