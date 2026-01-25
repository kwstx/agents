import pytest
import os
import time
import random
import json
from datetime import datetime
from utils.memory import Memory

DB_PATH = "tests/data/test_perf.db"

@pytest.fixture
def big_memory_db():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    mem = Memory(DB_PATH)
    
    # Seed Data
    # Create 10,000 records
    # Bulk insert for speed in setup
    data = []
    
    # We do manual bulk insert to avoid 10k commits in setup
    mem.conn.execute("BEGIN TRANSACTION;")
    query = "INSERT INTO memories (agent_id, type, content, timestamp, sim_context) VALUES (?, ?, ?, ?, ?)"
    
    for i in range(10000):
        aid = f"Agent_{i % 50}" # 50 agents
        typ = random.choice(["action", "observation", "failure", "message"])
        scenario = f"scen_{i % 20}"
        
        # Manually serialize to match what add_memory does
        content = f"\"content_{i}\"" 
        timestamp = datetime.now().isoformat()
        sim_context = json.dumps({"scenario": scenario, "complex": True})
        
        mem.conn.execute(query, (aid, typ, content, timestamp, sim_context))
        
    mem.conn.execute("COMMIT;")
    
    yield mem
    
    mem.close()
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass

def test_query_performance_large_dataset(big_memory_db):
    """Benchmark query performance with 10k records."""
    
    start = time.time()
    # Query: Specific Agent, Specific Type (Indexed?)
    results = big_memory_db.query_memory(agent_id="Agent_1", type="failure", limit=100)
    duration = time.time() - start
    
    print(f"\nQuery time for indexed search (Agent+Type): {duration:.4f}s")
    assert duration < 0.05, "Indexed query should be under 50ms"
    
    # Query: Filter by metadata (Full scan likely if not indexed properly, or python filtering)
    start = time.time()
    results = big_memory_db.query_memory(filter_metadata={"scenario": "scen_5"}, limit=50)
    duration = time.time() - start
    
    print(f"Query time for metadata search (Python filter): {duration:.4f}s")
    assert duration < 0.25, "Metadata query should be reasonably fast (<250ms) for 10k records"

if __name__ == "__main__":
    pass
