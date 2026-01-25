import pytest
import os
import concurrent.futures
import time
import random
from utils.memory import Memory

DB_PATH = "tests/data/test_memory_concurrency.db"

def worker_write(n_writes: int, agent_id: str):
    """Worker function to write multiple records to DB."""
    # Each thread/worker creates its own connection object (standard sqlite practice)
    mem = Memory(DB_PATH)
    for i in range(n_writes):
        mem.add_memory(
            agent_id=agent_id,
            type="stress_test",
            content=f"write_{i}",
            sim_context={"thread": agent_id, "iter": i}
        )
        # Random sleep to interleave writes
        # time.sleep(random.random() * 0.001) 
    mem.close()
    return n_writes

def test_concurrent_writes_integrity():
    """Simulate multiple agents writing simultaneously."""
    # Setup
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except: pass
    
    # Initialize DB (create table) before threading to avoid race condition on CREATE TABLE
    # Although CREATE TABLE IF NOT EXISTS is fairly safe, better to be clean.
    init_mem = Memory(DB_PATH)
    init_mem.close()

    NUM_WORKERS = 10
    WRITES_PER_WORKER = 100
    TOTAL_WRITES = NUM_WORKERS * WRITES_PER_WORKER
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = []
        for i in range(NUM_WORKERS):
            agent_id = f"Worker_{i}"
            futures.append(executor.submit(worker_write, WRITES_PER_WORKER, agent_id))
        
        results = [f.result() for f in futures]
    
    # Verify
    verify_mem = Memory(DB_PATH)
    rows = verify_mem.query_memory(limit=10000) # Get all
    
    verify_mem.close()
    
    # Cleanup
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except: pass
        
    assert len(rows) == TOTAL_WRITES
    assert sum(results) == TOTAL_WRITES
    
    # Verify content integrity of a random sample
    sample = rows[0]
    assert "Worker_" in sample["agent_id"]
    assert "write_" in str(sample["content"])

if __name__ == "__main__":
    # Allow running directly
    test_concurrent_writes_integrity()
    print("Concurrency test passed!")
