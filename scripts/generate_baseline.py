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

async def run_baseline_sim():
    # 1. Deterministic Seed
    SEED = 42
    random.seed(SEED)
    print(f"DEBUG: Random Seed set to {SEED}")

    # 2. Setup
    bus = MessageBus()
    await bus.start()
    
    # Use fixed config to avoid randomness in init if any
    env = WarehouseEnv(size=10, num_agents=2, config={"battery_drain": 0.5})
    engine = SimulationEngine(env) # Adversarial disabled by default
    
    agents = []
    agent_ids = ["Agent-0", "Agent-1"]
    
    # Init agents
    for a_id in agent_ids:
        # Note: WarehouseEnv.get_agent_state uses random.randint for position
        # Because we seeded random globally, this should be deterministic
        # Agent-0 will get same pos every time.
        env.get_agent_state(a_id) 
        
        agent = WarehouseAgent(a_id, bus, engine, behavior_config={"charge_threshold": 20.0})
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")

    # 3. Capture Trace
    trace = []
    
    # Run for 50 steps
    print("Running 50 deterministic steps...")
    for step in range(50):
        # We manually step agents logic to control execution order strictly?
        # Or let them run?
        # In the real code `warehouse_agent.py`, `run_logistics_loop` runs `while running: await step(); sleep(0.1)`
        # This relies on asyncio scheduling.
        # For a STRICT baseline, we might want to manually invoke agent.step() sequentially to remove scheduling variance.
        # But that changes the behavior from "Production" (Async).
        # Let's try running them manually to be 100% deterministic on logic first.
        # If we rely on asyncio.sleep(0.1) and internal scheduling, it *should* be fine in single thread, 
        # but let's be safer: We will invoke specific steps.
        
        step_snapshot = {"step": step, "agents": {}}
        
        for agent in agents:
            # Bypass the infinite loop and call step() directly
            await agent.step()
            
            # Capture state
            state = await engine.get_state(agent.agent_id)
            # IMPORTANT: state is a reference to Env internals. Must Copy!
            step_snapshot["agents"][agent.agent_id] = state.copy() 

        trace.append(step_snapshot)

    # 4. Save
    os.makedirs("tests", exist_ok=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump(trace, f, indent=2, sort_keys=True)
        
    print(f"Baseline saved to {os.path.abspath(BASELINE_FILE)}")
    # Cleanup
    for a in agents:
        await a.stop()
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_baseline_sim())
