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
# Use separate logs or just verify via analysis in logic
handler = logging.FileHandler('archetype_test.log', mode='w')
handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
root_logger.addHandler(handler)
logger = logging.getLogger("ArchetypeTest")

async def run_scenario(name, agent_config, duration=15):
    logger.info(f"\n>>> SCENARIO: {name} <<<")
    logger.info(f"Agent Config: {agent_config}")
    
    bus = MessageBus()
    await bus.start()
    
    # Use standard environment
    env = WarehouseEnv(size=8, num_agents=5)
    engine = SimulationEngine(env)
    
    agents = []
    for i in range(5):
        a_id = f"{name}-{i}"
        agent = WarehouseAgent(a_id, bus, engine, behavior_config=agent_config)
        env.get_agent_state(a_id) # Init
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    await asyncio.sleep(duration)
    
    # Collect Metrics
    deaths = 0
    deliveries = 0 # Need to parse logs for this ideally, or check agent state if we tracked it
    # We'll infer deliveries from logs in post-analysis or just check battery resilience
    
    # Check battery resilience
    min_battery = 100.0
    for a_id in env.agents:
        b = env.agents[a_id]["battery"]
        if b <= 0: deaths += 1
        if b < min_battery: min_battery = b
        
    logger.info(f"[{name}] Result: Deaths={deaths}, MinBattery={min_battery}")
    
    for a in agents: await a.stop()
    await bus.stop()

async def main():
    # Archetype 1: SpeedyBot (Aggressive)
    # waits until 5% battery to charge. Takes risks.
    await run_scenario(
        "Aggressive",
        {"charge_threshold": 5.0} # Very risky, might die in queue
    )
    
    # Archetype 2: SafeBot (Conservative)
    # Charges at 50%. Always topped up.
    await run_scenario(
        "Conservative",
        {"charge_threshold": 50.0}
    )

if __name__ == "__main__":
    asyncio.run(main())
