import pytest
import os
import time
from utils.memory import Memory

DB_PATH = "tests/data/test_summary.db"

@pytest.fixture
def mem_db():
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

def test_heuristic_summarization(mem_db):
    agent = "Agent_Noise"
    
    # 1. Unique Start
    mem_db.add_memory(agent, "act", "Start Mission")
    time.sleep(0.01)
    
    # 2. Repetitive Action (Noise)
    for _ in range(5):
        mem_db.add_memory(agent, "act", "Moved North")
        time.sleep(0.01)
        
    # 3. Unique Middle
    mem_db.add_memory(agent, "obs", "Found Wall")
    time.sleep(0.01)
    
    # 4. Another Repetition
    for _ in range(3):
        mem_db.add_memory(agent, "act", "Turned Right")
        time.sleep(0.01)
        
    # 5. Unique End
    mem_db.add_memory(agent, "act", "End Mission")
    
    # Generate Summary
    summary = mem_db.summarize_context(agent)
    
    print("\nGenerated Summary:")
    for line in summary:
        print(line)
        
    # Assertions
    # Needs to capture correct ordering and collapsing
    assert "Start Mission" in summary[0]
    
    # "Moved North" should be collapsed
    # Flexible check: "Moved North (x5)" or similar
    found_collapse_1 = any("Moved North (x5)" in s for s in summary)
    assert found_collapse_1, "Did not find collapsed 'Moved North (x5)'"
    
    # Check intermediate
    found_wall = any("Found Wall" in s for s in summary)
    assert found_wall
    
    # Check second collapse
    found_collapse_2 = any("Turned Right (x3)" in s for s in summary)
    assert found_collapse_2
    
    # Total length check: 1 + 1 + 1 + 1 + 1 = 5 lines expected
    # Start, Moved(x5), Wall, Turned(x3), End
    assert len(summary) == 5

if __name__ == "__main__":
    pass
