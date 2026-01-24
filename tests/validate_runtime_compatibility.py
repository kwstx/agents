import asyncio
import os
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger
from utils.message_bus import MessageBus
from agents.sim_adapter_agent import SimGridAgent

DB_PATH = "runtime_compat.db"
LOG_FILE = "runtime_compat.jsonl"

async def validate_runtime():
    print("Starting Runtime Compatibility Validation...")
    
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    
    # 1. Setup Infrastructure
    bus = MessageBus()
    await bus.start()
    
    # 2. Setup Environment with Latency
    env = GridWorld(size=5)
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    # 50ms latency to test async await chain
    stress_config = {"latency_range": (0.05, 0.05)} 
    engine = SimulationEngine(env, logger, stress_config)
    
    # 3. Setup Agent
    agent = SimGridAgent("SimBot-01", bus, engine)
    await agent.start()
    
    # 4. Subscribe to verification event
    event_received = asyncio.Event()
    final_payload = {}
    
    async def on_goal_reached(msg):
        print(f"EVENT RECEIVED: {msg.topic} from {msg.sender}")
        final_payload.update(msg.payload)
        event_received.set()
        
    bus.subscribe("goal_reached", on_goal_reached)
    
    # 5. Execute Task
    result = await agent.process_task("navigate_to_goal")
    
    # 6. Verify
    try:
        await asyncio.wait_for(event_received.wait(), timeout=2.0)
        print("SUCCESS: Goal Reached Event received.")
        print(f"Payload: {final_payload}")
        print(f"Transcript Length: {len(result)}")
        
        # Grid 5x5. Start (0,0). Goal (4,4). Min steps = 8.
        if final_payload["steps"] >= 8:
            print("Steps count valid.")
        else:
            print("WARNING: Steps count suspiciously low (teleportation?).")
            
    except asyncio.TimeoutError:
        print("FAILURE: Timed out waiting for goal_reached event.")
        
    # Cleanup
    await agent.stop()
    await bus.stop()
    try:
        os.remove(DB_PATH)
        os.remove(LOG_FILE)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(validate_runtime())
