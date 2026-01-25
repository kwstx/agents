import asyncio
import logging
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus

# Setup logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Overwrite file for clean run
handler = logging.FileHandler('refinement_test.log', mode='w')
handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
root_logger.addHandler(handler)
logger = logging.getLogger("RefinementTest")

async def run_generation(gen_id, threshold, duration=10):
    logger.info(f"\n>>> GENERATION {gen_id}: Threshold={threshold}% <<<")
    
    bus = MessageBus()
    await bus.start()
    
    # Grid size 6, 2 Agents (sparse enough to move, small enough to finish tasks)
    env = WarehouseEnv(size=6, num_agents=2)
    engine = SimulationEngine(env)
    
    agents = []
    for i in range(2):
        a_id = f"Gen{gen_id}-Bot-{i}"
        # Configure agent with current threshold
        config = {"charge_threshold": threshold}
        agent = WarehouseAgent(a_id, bus, engine, behavior_config=config)
        env.get_agent_state(a_id)
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    await asyncio.sleep(duration)
    
    # Evaluate Fitness
    total_deliveries = 0
    total_deaths = 0
    
    # We need to hackily count deliveries from logs or assume reward correlates
    # Since we don't have easy event logs access here without parsing, we'll rely on Battery State
    # and maybe 'carrying' state or just reward?
    # Let's trust that if they are alive and low battery, they *used* energy (working).
    # If they are dead, Bad.
    
    for a_id in env.agents:
        state = env.agents[a_id]
        if state["battery"] <= 0:
            total_deaths += 1
            
    # Simple Fitness Function
    # We want: Minimize Deaths, Maximize "Work" (implied by survival + aggressiveness)
    # If deaths > 0 -> Fitness = -100
    # Else -> Fitness = 100 - Threshold (Lower threshold = more uptime = better, if alive)
    
    fitness = 0
    if total_deaths > 0:
        fitness = -100
        logger.info(f"Gen {gen_id} Result: FAILURE (Deaths: {total_deaths})")
    else:
        fitness = 100 - threshold
        logger.info(f"Gen {gen_id} Result: SUCCESS (Deaths: 0, Fitness: {fitness})")

    for a in agents: await a.stop()
    await bus.stop()
    
    return fitness, total_deaths

async def main():
    # Optimization Loop
    # We want to find the lowest threshold that is safe.
    
    # 1. Start Conservative
    current_threshold = 60.0 # Very safe
    best_fitness = -999
    
    history = []
    
    # 3 Iterations
    for i in range(3):
        fitness, deaths = await run_generation(i, current_threshold)
        history.append((current_threshold, fitness, deaths))
        
        if fitness > best_fitness:
            best_fitness = fitness
        
        # Optimizer Logic
        if deaths > 0:
            # Too aggressive, pull back
            logger.info("-> Penalized! Increasing safety margin.")
            current_threshold += 30.0 # Big jump back
        else:
            # Safe, try to optimize (get greedier)
            logger.info("-> Safe! Pushing efficiency (lowering threshold).")
            current_threshold -= 20.0 # Aggressive cut
            
        if current_threshold < 5.0: current_threshold = 5.0 # Min Floor

    logger.info("\n>>> OPTIMIZATION SUMMARY <<<")
    for t, f, d in history:
        logger.info(f"Threshold: {t}%, Deaths: {d}, Fitness: {f}")

if __name__ == "__main__":
    asyncio.run(main())
