import asyncio
import os
import json
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from utils.memory import Memory

DB_PATH = "tests/data/verify_explainability.db"

class DetectiveAgent(BaseAgent):
    async def process_task(self, task):
        # 1. State Intent
        self.log_memory("intent", f"Investigating {task}")
        
        # 2. Observation (Context)
        sim_ctx = {"visibility": "low", "noise_level": "high"}
        self.log_memory("observation", "Found muddy footprint", sim_context=sim_ctx)
        
        # 3. Decision/Reasoning
        self.log_memory("reasoning", "Footprint suggests recent entry. Proceeding with caution.")
        
        # 4. Action
        self.log_memory("action", "Follow footprint North")
        
        # 5. Outcome
        self.state["status"] = "alert"
        # Sanitize state
        safe_state = self.state.copy()
        if "last_active" in safe_state: safe_state["last_active"] = str(safe_state["last_active"])
        
        self.log_memory("outcome", "Discovered hidden door", sim_context={"new_state": safe_state})
        print("DEBUG: Outcome logged.")

    async def setup_memory(self):
        if not self.memory_module:
            self.memory_module = Memory(DB_PATH)

async def generate_history():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    bus = MessageBus()
    agent = DetectiveAgent("Sherlock", bus)
    await agent.start()
    await agent.add_task("CrimeScene_01")
    await asyncio.sleep(0.1)
    await agent.stop()
    agent.memory_module.close()

def generate_report():
    mem = Memory(DB_PATH)
    logs = mem.query_memory(agent_id="Sherlock", limit=20)
    logs.reverse() # Chronological
    
    print("\n=== AGENT SH ERLOCK: INVESTIGATION REPORT ===\n")
    
    curr_task = None
    
    for log in logs:
        ts = log["timestamp"]
        typ = log["type"]
        content = log["content"]
        ctx = log["sim_context"]
        
        # Heuristic Formatting
        if typ == "task_started":
            curr_task = content
            print(f"[{ts}] ⭐ GOAL STARTED: {content}")
        
        elif typ == "intent":
             print(f"[{ts}] 🧠 INTENT: {content}")
             
        elif typ == "observation":
             extras = f"(Context: {ctx})" if ctx else ""
             print(f"[{ts}] 👁️ OBSERVED: {content} {extras}")
             
        elif typ == "reasoning":
             print(f"[{ts}] 🤔 THOUGHT: {content}")
             
        elif typ == "action":
             print(f"[{ts}] ⚡ ACTION: {content}")
             
        elif typ == "outcome":
             print(f"[{ts}] ✅ RESULT: {content}")
             
        elif typ == "task_completed":
             print(f"[{ts}] 🏁 FINISHED: {content}")
             
        elif typ == "task_error":
             print(f"[{ts}] ❌ CRASH: {content}")

    print("\n=============================================")
    
    # Validation
    # We check if the narrative contains key elements
    # Check if specific strings exist in any log's content
    # Note: content might be stored as quoted JSON string or raw string depending on memory add method
    
    # "Found muddy footprint"
    footprint_exists = any("Found muddy footprint" in str(l["content"]) for l in logs)
    # "Discovered hidden door"
    door_exists = any("Discovered hidden door" in str(l["content"]) for l in logs)
    
    assert footprint_exists, "Report missing expected observation: 'Found muddy footprint'"
    assert door_exists, "Report missing expected outcome: 'Discovered hidden door'"
    print("\nValidation: Narrative successfully reconstructed from raw logs.")

if __name__ == "__main__":
    asyncio.run(generate_history())
    generate_report()
