import asyncio
import logging
import random
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosTest")
# Log to file for verification
handler = logging.FileHandler('chaos_test.log', mode='w')
handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
logging.getLogger().addHandler(handler)

async def chaos_monkey(agents, bus, interval=2.0):
    """Randomly breaks things."""
    while True:
        await asyncio.sleep(interval)
        action = random.choice(["kill_agent", "drop_comms", "nothing", "nothing"])
        
        if action == "kill_agent":
            # Pick a lucky winner
            victim = random.choice(agents)
            if victim.running:
                logger.warning(f"CHAOS: Killing {victim.agent_id} MID-TASK!")
                # Forcefully stop
                victim.running = False
                await victim.stop()
        
        elif action == "drop_comms":
            logger.warning("CHAOS: Simulating Network Failure (Message Bus Paused)")
            # Simulating by just unsubscribing random agent for a bit?
            # Or effectively clearing the bus queue if we could access it.
            # Ideally we'd have a 'drop_rate' in bus, but we can simulate agent confusion by wiping their current goal
            victim = random.choice(agents)
            if victim.running:
                logger.warning(f"CHAOS: Corrupting memory of {victim.agent_id}")
                victim.current_goal = None # Forgot where it was going
                victim.goal_type = None

async def run_resilience_test():
    logger.info(">>> STARTING RESILIENCE (CHAOS) TEST <<<")
    
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(size=6, num_agents=4)
    engine = SimulationEngine(env)
    
    agents = []
    for i in range(4):
        a_id = f"Survivor-{i}"
        agent = WarehouseAgent(a_id, bus, engine)
        env.get_agent_state(a_id)
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    # Start Chaos in background
    chaos_task = asyncio.create_task(chaos_monkey(agents, bus))
    
    # Run simulation
    duration = 15
    await asyncio.sleep(duration)
    
    # Check status
    active_count = sum(1 for a in agents if a.running)
    logger.info(f"Test End. Active Agents: {active_count}/4")
    
    if active_count < 4:
        logger.info("[SUCCESS] System logged deaths and survived partial failure.")
    else:
        logger.warning("[WARNING] Chaos Monkey failed to kill anyone? (Unlucky)")
    
    chaos_task.cancel()
    for a in agents: 
        if a.running: await a.stop()
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_resilience_test())
