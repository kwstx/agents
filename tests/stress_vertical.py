import asyncio
import logging
import json
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus

# Setup logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('stress_test.log', mode='w')
handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
root_logger.addHandler(handler)
logger = logging.getLogger("VerticalStress")

async def run_stress_test(name, env_config, agent_count, duration=10):
    logger.info(f"\n>>> START STRESS TEST: {name} <<<")
    logger.info(f"Config: {env_config}, Agents: {agent_count}")
    
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(**env_config, num_agents=agent_count)
    engine = SimulationEngine(env)
    
    agents = []
    for i in range(agent_count):
        a_id = f"Agent-{i}"
        agent = WarehouseAgent(a_id, bus, engine)
        env.get_agent_state(a_id) # Init state
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    await asyncio.sleep(duration)
    
    # Analysis
    logger.info(f"--- Analyzing Results for {name} ---")
    collisions = 0
    deaths = 0
    deliveries = 0
    
    # We need to peek at internal event logs or states since we aren't using the full dashboard pipeline here
    # Just check final states for deaths and rough collision penalty counts from rewards (if we tracked them)
    # Actually, WarehouseEnv doesn't store history. We rely on the agents being dead or alive.
    
    for a_id in env.agents:
        state = env.agents[a_id]
        if state["battery"] <= 0:
            deaths += 1
            
    # For collisions, we can't easily see history without the logger attached.
    # But for High Density, we expect widespread gridlock (agents not moving).
    # We can check if agents are at their spawn points or clumped.
    
    logger.info(f"Result: {deaths}/{agent_count} Agents Died.")
    
    for a in agents: await a.stop()
    await bus.stop()
    
async def main():
    # Test 1: High Density (Crowding)
    # 5x5 grid = 25 tiles. 20 agents = 80% occupancy.
    # Expected: High contention, gridlock, low throughput.
    await run_stress_test(
        name="High Density (80% Occupancy)",
        env_config={"size": 5},
        agent_count=20,
        duration=10
    )
    
    # Test 2: Resource Scarcity (Battery Drain)
    # Normal density, but battery drains 5% per step (usually 0.5%).
    # Expected: Massive die-off before reaching chargers.
    await run_stress_test(
        name="Resource Scarcity (10x Battery Drain)",
        env_config={"size": 10, "config": {"battery_drain": 5.0}},
        agent_count=5,
        duration=10
    )

if __name__ == "__main__":
    asyncio.run(main())
