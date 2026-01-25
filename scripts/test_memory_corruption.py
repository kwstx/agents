
import sqlite3
import json
import sys
import os
from utils.memory import Memory

DB_PATH = "data/memory.db"

def test_corruption():
    if not os.path.exists(DB_PATH):
        print(f"FAIL: {DB_PATH} not found.")
        sys.exit(1)
        
    print("--- Injecting Corruption ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Insert a valid looking row but with corrupted JSON content
    bad_json = '{"key": "value", BROKEN_JSON'
    
    try:
        cursor.execute("""
            INSERT INTO memories (agent_id, type, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, ("TEST_CORRUPT", "error_test", bad_json, "2024-01-01T00:00:00"))
        conn.commit()
        print("Injected corrupted record.")
    except Exception as e:
        print(f"Injection failed (this is unexpected, sqlite assumes text): {e}")
        sys.exit(1)
        
    conn.close()
    
    print("--- Verifying Resilience ---")
    memory_mod = Memory(db_path=DB_PATH)
    
    try:
        # This query should hit the bad record
        results = memory_mod.query_memory(agent_id="TEST_CORRUPT", limit=10)
        print(f"Query returned {len(results)} records.")
        
        # Check if any result is the bad one?
        # If Memory module eats the exception, it might exclude the row or return raw string?
        # Let's check Memory implementation.
        # It typically does `json.loads(row[content])`.
        # If that fails, what does it do?
        
        # We need to verify it didn't crash.
        print("SUCCESS: System did not crash on corrupted memory.")
        
    except Exception as e:
        print(f"FAIL: System crashed reading corrupted memory: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_corruption()
