import asyncio
import logging
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus
from utils.interaction_logger import InteractionLogger

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WarehouseSim")

async def run_sim():
    # 1. Setup Infrastructure
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(size=10, num_agents=3)
    # Logger saves to logs/warehouse_sim.jsonl
    sim_logger = InteractionLogger(db_path="logs/warehouse_sim.db", log_file="logs/warehouse_sim.jsonl") 
    engine = SimulationEngine(env, logger=sim_logger)
    
    # 2. Setup Agents
    agents = []
    for i in range(3):
        agent_id = f"LogisticsBot-{i+1}"
        agent = WarehouseAgent(agent_id, bus, engine)
        agents.append(agent)
        
    # 3. Start
    logger.info("Starting Simulation...")
    for agent in agents:
        await agent.start()
        await agent.add_task("start_logistics")
        
    # 4. Run for duration
    try:
        await asyncio.sleep(30) # Run for 30 seconds
    except KeyboardInterrupt:
        pass
        
    # 5. Shutdown
    logger.info("Stopping Simulation...")
    for agent in agents:
        await agent.stop()
    await bus.stop()
    logger.info("Simulation Complete.")

if __name__ == "__main__":
    asyncio.run(run_sim())
