import unittest
import shutil
import os
import asyncio
from models.decision_model import GridDecisionModel
from models.trainer import DQNTrainer
from utils.memory import Memory

class TestMemoryIntegrity(unittest.TestCase):
    def test_replay_buffer_decay(self):
        print("\nTest 1: Replay Buffer Decay")
        model = GridDecisionModel()
        trainer = DQNTrainer(model)
        
        # Manually set small maxlen for testing
        trainer.memory = type(trainer.memory)(maxlen=10)
        
        # Add 15 items
        for i in range(15):
             trainer.store_experience([i], 0, 0, [i+1], False)
             
        self.assertEqual(len(trainer.memory), 10, "Buffer should not exceed maxlen")
        
        # Verify oldest was removed (should contain 5..14)
        first_item = trainer.memory[0]
        self.assertEqual(first_item[0], [5], "Oldest items should be evicted")
        print("SUCCESS: Replay Buffer maintained size and evicted old items.")

    def test_summary_condensation(self):
        print("\nTest 2: Semantic Summary Integrity")
        db_path = "tests/temp_memory_test.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            
        mem = Memory(db_path=db_path)
        agent_id = "SummaryTester"
        
        # Add repetitive logs
        for _ in range(10):
            mem.add_memory(agent_id, "test", "Moved Right")
            
        mem.add_memory(agent_id, "test", "Moved Up")
        
        for _ in range(5):
             mem.add_memory(agent_id, "test", "Moved Right")
             
        # Call summarize
        summary = mem.summarize_context(agent_id, limit=50)
        print(f"Summary: {summary}")
        
        # Expected: ["Moved Right (x10)", "Moved Up", "Moved Right (x5)"]
        # Note: summarize_context returns chronological list (oldest to newest)? 
        # Wait, the code says:
        # raw_memories = self.get_recent(agent_id, limit) -> Returns DESC (newest first)
        # raw_memories.reverse() -> Now Ascending (Oldest first)
        # So yes, order should be correct.
        
        expected_items = ["Moved Right (x10)", "Moved Up", "Moved Right (x5)"]
        self.assertEqual(summary, expected_items, "Summary did not condense correctly")
        
        mem.close()
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
            
        print("SUCCESS: Summarizer condensed duplicate logs.")

if __name__ == "__main__":
    unittest.main()
