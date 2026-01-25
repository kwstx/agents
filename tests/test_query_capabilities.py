import pytest
import os
import time
from datetime import datetime, timedelta
from utils.memory import Memory

DB_PATH = "tests/data/test_query.db"

@pytest.fixture
def memory_db():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    mem = Memory(DB_PATH)
    yield mem
    mem.close()
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass

def test_query_filtering(memory_db):
    # Setup Data
    # Agent A, Type X, Context 1
    memory_db.add_memory("Agent_A", "X", "msg1", sim_context={"scenario": "test_1", "run": 1})
    time.sleep(0.01) # Ensure distinct timestamps
    
    # Agent A, Type Y, Context 1
    memory_db.add_memory("Agent_A", "Y", "msg2", sim_context={"scenario": "test_1", "run": 1})
    time.sleep(0.01)
    
    # Agent B, Type X, Context 2
    memory_db.add_memory("Agent_B", "X", "msg3", sim_context={"scenario": "test_2", "run": 1})
    
    # Test 1: Filter by Agent
    res = memory_db.query_memory(agent_id="Agent_A")
    assert len(res) == 2
    
    # Test 2: Filter by Type
    res = memory_db.query_memory(type="X")
    assert len(res) == 2 # msg1 and msg3
    
    # Test 3: Filter by Metadata (sim_context)
    res = memory_db.query_memory(filter_metadata={"scenario": "test_1"})
    assert len(res) == 2
    
    res = memory_db.query_memory(filter_metadata={"scenario": "test_2"})
    assert len(res) == 1
    assert res[0]["agent_id"] == "Agent_B"

def test_time_range_query(memory_db):
    # Create logs with specific times
    # Note: timestamps are set inside add_memory using datetime.now(), so we can't inject past times easily 
    # unless we modify add_memory or insert manually.
    # For this test, we accept 'now' and just sleep.
    
    t0 = datetime.now().isoformat()
    memory_db.add_memory("A", "T", "early")
    time.sleep(0.1)
    
    t1 = datetime.now().isoformat() # Mid point
    time.sleep(0.1)
    
    memory_db.add_memory("A", "T", "late")
    t2 = datetime.now().isoformat()
    
    # Query all
    res = memory_db.query_memory()
    assert len(res) == 2
    
    # Query after t1 (should only get "late")
    res = memory_db.query_memory(start_time=t1)
    assert len(res) == 1
    assert res[0]["content"] == "late"
    
    # Query before t1 (should only get "early")
    # Note: timestamp of "early" is < t1.
    res = memory_db.query_memory(end_time=t1)
    assert len(res) == 1
    assert res[0]["content"] == "early"

if __name__ == "__main__":
    pass
