import asyncio
import logging
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from utils.message_bus import MessageBus

# Setup logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('validation.log', mode='w')
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)
logger = logging.getLogger("ProblemValidator")

class CorridorEnv(WarehouseEnv):
    """Forces agents into a 1D line (y=0) to simulate a hallway."""
    def step(self, action: str, agent_id: str = "default"):
        # Pre-check: If trying to move Y!=0, block it (Wall)
        state = self.get_agent_state(agent_id)
        x, y = state["position"]
        
        # Virtual Walls at y!=0
        if action == "UP" or (action == "DOWN" and y == 0):
             return state, -1.0, False, {"valid_action": False, "event": "wall_hit"}
             
        return super().step(action, agent_id)

async def test_charging_death_spiral():
    logger.info(">>> TEST: CHARGING DEATH SPIRAL <<<")
    bus = MessageBus()
    await bus.start()
    
    env = WarehouseEnv(size=5, num_agents=5)
    engine = SimulationEngine(env)
    
    # Setup Agents with CRITICAL battery
    agents = []
    for i in range(5):
        a_id = f"StarvingBot-{i}"
        agent = WarehouseAgent(a_id, bus, engine)
        
        # FORCE STATE
        env.get_agent_state(a_id) # Init
        env.agents[a_id]["battery"] = 15.0 # Just enough to reach charger if lucky
        env.agents[a_id]["position"] = (i, 0) # Scatter them
        
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")

    # Run for 15 seconds
    logger.info("Simulating contention...")
    await asyncio.sleep(15)
    
    # Check Dead Agents
    dead_count = 0
    for a_id in env.agents:
        if env.agents[a_id]["battery"] <= 0:
            dead_count += 1
            
    logger.info(f"Result: {dead_count}/5 Agents Died.")
    if dead_count >= 2:
        logger.info("[SUCCESS] Hypothesis Verified: Queue killed agents.")
    else:
        logger.warning("[FAILURE] Agents survived? Too efficient?")

    for a in agents: await a.stop()
    await bus.stop()

async def test_hallway_deadlock():
    logger.info("\n>>> TEST: HALLWAY DEADLOCK <<<")
    bus = MessageBus()
    await bus.start()
    
    env = CorridorEnv(size=5, num_agents=2)
    engine = SimulationEngine(env)
    
    # Setup Agent Left and Agent Right
    # Left moves Right, Right moves Left
    a1 = WarehouseAgent("LeftBot", bus, engine)
    a2 = WarehouseAgent("RightBot", bus, engine)
    
    # Init and Force Positions
    env.get_agent_state("LeftBot")
    env.agents["LeftBot"]["position"] = (0, 0)
    
    env.get_agent_state("RightBot")
    env.agents["RightBot"]["position"] = (4, 0)
    
    # Monkey Patch Goals (since they auto-decide)
    # We want them to collide.
    # We'll just let them run. WarehouseAgent goes to Pickup (x=0) or Dropoff (x=size-1).
    # If LeftBot has item, it goes to 4. If RightBot is idle, it goes to 0.
    
    # Force LeftBot to have item -> wants 4
    env.agents["LeftBot"]["carrying"] = "package"
    
    # Force RightBot to be empty -> wants 0 (Pickup zone is x=0)
    env.agents["RightBot"]["carrying"] = None 
    
    await a1.start()
    await a2.start()
    await a1.add_task("start_logistics")
    await a2.add_task("start_logistics")
    
    logger.info("Simulating head-on collision course...")
    await asyncio.sleep(5)
    
    p1 = env.agents["LeftBot"]["position"]
    p2 = env.agents["RightBot"]["position"]
    
    logger.info(f"Final Positions: LeftBot{p1}, RightBot{p2}")
    
    # If they passed each other, p1.x > p2.x (roughly)
    # If they are stuck, they are adjacent or same.
    # Since we added collision logic, they should effectively stop at (1,0) and (2,0) or similar.
    
    if abs(p1[0] - p2[0]) <= 1:
        logger.info("[SUCCESS] Hypothesis Verified: Agents are stuck/adjacent.")
    else:
        logger.warning("[FAILURE] Agents ghosted through each other!")

    await a1.stop()
    await a2.stop()
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(test_charging_death_spiral())
    asyncio.run(test_hallway_deadlock())
