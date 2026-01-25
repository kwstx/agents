import pytest
import asyncio
import os
import json
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus
from utils.memory import Memory

DB_PATH = "tests/data/verify_context.db"

class ContextAwareAgent(BaseAgent):
    """Agent that receives simulation parameters."""
    def __init__(self, agent_id, bus, sim_params: dict):
        super().__init__(agent_id, bus)
        self.sim_params = sim_params

    async def process_task(self, task):
        # In a real simulation, the environment might pass these, 
        # or the agent has them injected at startup.
        
        # Merge sim params with local task context
        ctx = self.sim_params.copy()
        ctx["task_specific_flag"] = "verified"
        
        self.log_memory("action", f"Executing {task}", sim_context=ctx)
        
        if self.sim_params.get("failure_mode") == "network_lag":
            self.log_memory("observation", "high_latency_detected", sim_context=ctx)

    async def setup_memory(self):
        if not self.memory_module:
            self.memory_module = Memory(DB_PATH)

async def run_context_scenario():
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    bus = MessageBus()
    
    # Run 1: Normal Scenario
    params_normal = {"scenario_id": "SCEN_001", "failure_mode": "none", "latency_ms": 10}
    agent1 = ContextAwareAgent("Agent_Normal", bus, params_normal)
    await agent1.start()
    await agent1.add_task("Routine_Patrol")
    await asyncio.sleep(0.1)
    await agent1.stop()
    agent1.memory_module.close()
    
    # Run 2: High Latency Scenario
    params_lag = {"scenario_id": "SCEN_002", "failure_mode": "network_lag", "latency_ms": 500}
    agent2 = ContextAwareAgent("Agent_Lagged", bus, params_lag)
    await agent2.start()
    await agent2.add_task("Routine_Patrol")
    await asyncio.sleep(0.1)
    await agent2.stop()
    agent2.memory_module.close()

def test_simulation_context_accuracy():
    asyncio.run(run_context_scenario())
    
    mem = Memory(DB_PATH)
    
    # 1. Query by Scenario ID (SCEN_001)
    logs_scen1 = mem.query_memory(filter_metadata={"scenario_id": "SCEN_001"})
    print(f"Scenario 1 Logs: {len(logs_scen1)}")
    
    assert len(logs_scen1) > 0
    for l in logs_scen1:
        assert l["sim_context"]["scenario_id"] == "SCEN_001"
        assert l["sim_context"]["latency_ms"] == 10
        
    # 2. Query by Failure Mode (network_lag)
    logs_lag = mem.query_memory(filter_metadata={"failure_mode": "network_lag"})
    print(f"Lag Logs: {len(logs_lag)}")
    
    # Expect at least 'action' and 'observation'
    assert len(logs_lag) >= 2 
    
    # Check specific observation "high_latency_detected"
    lag_obs = next((l for l in logs_lag if l["content"] == "\"high_latency_detected\"" or l["content"] == "high_latency_detected"), None)
    assert lag_obs is not None, "Failed to find context-specific observation"
    assert lag_obs["sim_context"]["latency_ms"] == 500
    
    # 3. Cross-Validation: Ensure no cross-contamination
    # Logs from SCEN_001 should NOT appear in SCEN_002 query result
    logs_scen2 = mem.query_memory(filter_metadata={"scenario_id": "SCEN_002"})
    for l in logs_scen2:
        assert l["agent_id"] == "Agent_Lagged"
        assert l["sim_context"]["failure_mode"] == "network_lag"
        
    print("SUCCESS: Simulation contexts matches query filters perfectly.")

if __name__ == "__main__":
    test_simulation_context_accuracy()
