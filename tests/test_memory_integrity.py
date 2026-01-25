import pytest
import shutil
import os
import json
from utils.memory import Memory

DB_PATH = "tests/data/test_memory_integrity.db"

@pytest.fixture
def memory_db():
    # Setup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    dirname = os.path.dirname(DB_PATH)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
        
    mem = Memory(DB_PATH)
    yield mem
    # Teardown
    mem.close()
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            pass # Sometimes windows holds lock briefly

def test_persistence_basic(memory_db):
    """Verify that data written is persisted after close/reopen."""
    memory_db.add_memory("Agent_X", "action", "Moved North")
    
    # Close and Re-open to simulate restart
    memory_db.close()
    
    mem2 = Memory(DB_PATH)
    results = mem2.query_memory("Agent_X")
    
    assert len(results) == 1
    assert results[0]["content"] == "Moved North"
    assert results[0]["agent_id"] == "Agent_X"
    mem2.close()

def test_schema_full_fields():
    """Verify all schema fields are stored and retrieved correctly."""
    mem = Memory(DB_PATH + "_schema")
    
    complex_content = {"target": "box", "velocity": 0.5}
    sim_context = {"weather": "rainy", "tick": 100}
    
    mem.add_memory(
        agent_id="Agent_Y",
        type="observation",
        content=complex_content,
        sim_context=sim_context
    )
    
    results = mem.query_memory(agent_id="Agent_Y")
    entry = results[0]
    
    assert entry["type"] == "observation"
    assert isinstance(entry["content"], dict)
    assert entry["content"]["target"] == "box"
    assert entry["sim_context"]["weather"] == "rainy"
    # Timestamp should exist and be a string
    assert isinstance(entry["timestamp"], str)
    
    mem.close()
    
    if os.path.exists(DB_PATH + "_schema"):
        try:
             os.remove(DB_PATH + "_schema")
        except: pass

def test_json_serialization_handling():
    """Ensure non-primitive types are auto-serialized if possible or handled."""
    mem = Memory(DB_PATH + "_json")
    
    # List content
    mem.add_memory("Agent_Z", "list_test", [1, 2, 3])
    
    results = mem.query_memory("Agent_Z")
    assert results[0]["content"] == [1, 2, 3]
    
    mem.close()
    if os.path.exists(DB_PATH + "_json"):
        try:
             os.remove(DB_PATH + "_json")
        except: pass
