import asyncio
import logging
import os
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus
from utils.interaction_logger import InteractionLogger

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataGen")

async def run_data_gen():
    logger.info(">>> GENERATING DASHBOARD DATA <<<")
    
    # Ensure logs dir
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    db_path = "logs/warehouse_sim.db"
    # Clean old db
    if os.path.exists(db_path):
        os.remove(db_path)
        
    interaction_logger = InteractionLogger(db_path=db_path, log_file="logs/events.jsonl")
    
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(size=8, num_agents=4)
    # Pass logger to engine
    engine = SimulationEngine(env, logger=interaction_logger)
    
    agents = []
    # Mix of archetypes to get diverse data
    archetypes = [
        {"name": "Speedy-01", "config": {"charge_threshold": 10.0}},
        {"name": "Speedy-02", "config": {"charge_threshold": 10.0}},
        {"name": "Safe-01", "config": {"charge_threshold": 50.0}},
        {"name": "Safe-02", "config": {"charge_threshold": 50.0}},
    ]
    
    for arc in archetypes:
        a_id = arc["name"]
        agent = WarehouseAgent(a_id, bus, engine, behavior_config=arc["config"])
        env.get_agent_state(a_id)
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    # Run for 20 seconds to populate stats
    logger.info("Running simulation loop...")
    await asyncio.sleep(20)
    
    for a in agents: await a.stop()
    await bus.stop()
    logger.info(">>> DATA GENERATION COMPLETE <<<")

if __name__ == "__main__":
    asyncio.run(run_data_gen())
