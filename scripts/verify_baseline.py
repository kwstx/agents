import random
import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.envs.warehouse_agent import WarehouseAgent
from agent_forge.utils.message_bus import MessageBus

BASELINE_FILE = "tests/baseline_truth.json"

async def verify_baseline():
    if not os.path.exists(BASELINE_FILE):
        print(f"ERROR: Baseline file {BASELINE_FILE} not found. Run generate_baseline.py first.")
        sys.exit(1)

    with open(BASELINE_FILE, "r") as f:
        expected_trace = json.load(f)

    # 1. Deterministic Seed
    SEED = 42
    random.seed(SEED)
    
    # 2. Setup (Identical to generate_baseline.py)
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(size=10, num_agents=2, config={"battery_drain": 0.5})
    engine = SimulationEngine(env)
    
    agents = []
    agent_ids = ["Agent-0", "Agent-1"]
    
    for a_id in agent_ids:
        env.get_agent_state(a_id) 
        agent = WarehouseAgent(a_id, bus, engine, behavior_config={"charge_threshold": 20.0})
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")

    # 3. Validation Loop
    print(f"Verifying {len(expected_trace)} steps against baseline...")
    
    for i, expected_step in enumerate(expected_trace):
        # Run step
        actual_step = {"step": i, "agents": {}}
        for agent in agents:
            await agent.step()
            state = await engine.get_state(agent.agent_id)
            actual_step["agents"][agent.agent_id] = state

        # Compare
        # Serialize/Deserialize to ensure float formatting matches json dump
        actual_json = json.loads(json.dumps(actual_step))
        
        if actual_json != expected_step:
            print(f"MISMATCH at Step {i}!")
            print(f"Expected: {expected_step}")
            print(f"Actual:   {actual_json}")
            sys.exit(1)

    print("SUCCESS: Simulation matches baseline exactly.")

    # Cleanup
    for a in agents:
        await a.stop()
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(verify_baseline())
