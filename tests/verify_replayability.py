import asyncio
import logging
import random
import json
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ReplayTest")
logger.setLevel(logging.INFO)

async def run_deterministic_trace(seed, steps=20):
    """
    Runs a simulation with a fixed seed manually stepping agents.
    Returns a trace of agent states.
    """
    # Force Seed
    random.seed(seed)
    
    bus = MessageBus()
    await bus.start()
    
    # 5x5 grid, 2 Agents
    env = WarehouseEnv(size=5, num_agents=2)
    engine = SimulationEngine(env)
    
    agents = []
    agent_ids = []
    
    for i in range(2):
        a_id = f"Agent-{i}"
        agent = WarehouseAgent(a_id, bus, engine, behavior_config={"charge_threshold": 20})
        # Force initial state explicitly?
        # Env.get_agent_state calls random.randint. Since we seeded above, this is deterministic effectively.
        env.get_agent_state(a_id)
        
        agents.append(agent)
        agent_ids.append(a_id)
        # Note: We do NOT call agent.start() or add_task.
        # We manually step them.
        agent.running = True
        
    trace = []
    
    # Run Steps
    for step_num in range(steps):
        step_snapshot = {}
        for agent in agents:
            # Execute one logic cycle
            await agent.step()
            
            # Record State
            state = env.agents[agent.agent_id]
            step_snapshot[agent.agent_id] = {
                "pos": state["position"],
                "battery": state["battery"],
                "carrying": state["carrying"]
            }
        trace.append(step_snapshot)
        
    await bus.stop()
    return trace

async def main():
    logger.info(">>> TEST: REPLAYABILITY (Determinism) <<<")
    
    seed = 42
    logger.info(f"Running Trace 1 (Seed={seed})...")
    trace1 = await run_deterministic_trace(seed)
    
    logger.info(f"Running Trace 2 (Seed={seed})...")
    trace2 = await run_deterministic_trace(seed)
    
    logger.info(f"Running Trace 3 (Seed={seed+1})...")
    trace3 = await run_deterministic_trace(seed + 1)
    
    # Compare 1 and 2
    if json.dumps(trace1) == json.dumps(trace2):
        logger.info("[SUCCESS] Trace 1 == Trace 2 (Identical Seeds produce Identical Runs)")
    else:
        logger.error("[FAILURE] Trace 1 != Trace 2 (Non-deterministic!)")
        # Diff
        for i in range(len(trace1)):
            if trace1[i] != trace2[i]:
                logger.error(f"Divergence at Step {i}:")
                logger.error(f"Run1: {trace1[i]}")
                logger.error(f"Run2: {trace2[i]}")
                break
                
    # Compare 1 and 3
    if json.dumps(trace1) != json.dumps(trace3):
        logger.info("[SUCCESS] Trace 1 != Trace 3 (Different Seeds produce Different Runs)")
    else:
        logger.warning("[WARNING] Trace 1 == Trace 3 (Seed didn't affect outcome?)")

if __name__ == "__main__":
    asyncio.run(main())
