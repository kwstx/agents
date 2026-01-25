import pytest
import asyncio
import os
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from utils.memory import Memory

DB_PATH = "tests/data/verify_isolation.db"

class SecretAgent(BaseAgent):
    async def process_task(self, task):
        self.log_memory("secret", f"My Secret: {task}")

    async def setup_memory(self):
        if not self.memory_module:
            self.memory_module = Memory(DB_PATH)

async def run_isolation_scenario():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    bus = MessageBus()
    
    # Agent 007
    bond = SecretAgent("007", bus)
    await bond.start()
    await bond.add_task("LicenseToKill")
    await asyncio.sleep(0.1)
    
    # Agent 006 (Traitor)
    trevelyan = SecretAgent("006", bus)
    await trevelyan.start()
    await trevelyan.add_task("GoldenEye")
    await asyncio.sleep(0.1)
    
    # TEST 1: Strict Isolation via Standard API
    # 007 tries to recall
    memories_007 = bond.recall_memories()
    print(f"\n007 Memories: {[m['content'] for m in memories_007]}")
    
    # 006 tries to recall
    memories_006 = trevelyan.recall_memories()
    print(f"006 Memories: {[m['content'] for m in memories_006]}")
    
    # VERIFY 1: Content Isolation
    has_007_secret = any("LicenseToKill" in str(m["content"]) for m in memories_007)
    has_006_secret_in_007 = any("GoldenEye" in str(m["content"]) for m in memories_007)
    
    assert has_007_secret, "007 lost his own secret!"
    assert not has_006_secret_in_007, "SECURITY BREACH: 007 read 006's memory!"
    
    # VERIFY 2: Cross-Check
    has_006_secret = any("GoldenEye" in str(m["content"]) for m in memories_006)
    has_007_secret_in_006 = any("LicenseToKill" in str(m["content"]) for m in memories_006)
    
    assert has_006_secret, "006 lost his own secret!"
    assert not has_007_secret_in_006, "SECURITY BREACH: 006 read 007's memory!"
    
    await bond.stop()
    await trevelyan.stop()
    if bond.memory_module: bond.memory_module.close()
    if trevelyan.memory_module: trevelyan.memory_module.close()
    
    print("\nSUCCESS: Agents contain strictly isolated memory streams.")

def test_memory_isolation_logic():
    asyncio.run(run_isolation_scenario())

if __name__ == "__main__":
    test_memory_isolation_logic()
