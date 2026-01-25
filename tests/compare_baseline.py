import asyncio
import logging
import time
from environments.warehouse_env import WarehouseEnv
from environments.simulation_engine import SimulationEngine
from agents.warehouse_agent import WarehouseAgent
from agents.baseline_agent import RandomBaselineAgent
from utils.message_bus import MessageBus
from utils.interaction_logger import InteractionLogger

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("BaselineComp")
logger.setLevel(logging.INFO)

async def run_scenario(scenario_name, agent_class, duration=30):
    logger.info(f"\n>>> RUNNING SCENARIO: {scenario_name} <<<")
    
    # DB for metrics
    db_name = f"logs/comp_{scenario_name}.db"
    import os
    if os.path.exists(db_name): os.remove(db_name)
    
    interaction_logger = InteractionLogger(db_path=db_name, log_file=f"logs/{scenario_name}.jsonl")
    
    bus = MessageBus()
    await bus.start()
    
    # 5 Agents on 8x8 grid
    env = WarehouseEnv(size=8, num_agents=5)
    engine = SimulationEngine(env, logger=interaction_logger)
    
    agents = []
    for i in range(5):
        a_id = f"{scenario_name}-{i}"
        if agent_class == WarehouseAgent:
            agent = WarehouseAgent(a_id, bus, engine)
        else:
            agent = RandomBaselineAgent(a_id, bus, engine)
        env.get_agent_state(a_id)
        agents.append(agent)
        await agent.start()
        await agent.add_task("start_logistics")
        
    start_time = time.time()
    await asyncio.sleep(duration)
    
    # Collect Metrics from DB
    import sqlite3
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT metadata FROM interactions")
    rows = c.fetchall()
    conn.close()
    
    import json
    deliveries = 0
    deaths = 0
    for r in rows:
        try:
            m = json.loads(r[0])
            if m.get("event") == "delivered": deliveries += 1
            if m.get("event") == "battery_depleted": deaths += 1
        except: pass
        
    logger.info(f"[{scenario_name}] Results ({duration}s):")
    logger.info(f"  Deliveries: {deliveries}")
    logger.info(f"  Deaths:     {deaths}")
    
    for a in agents: await a.stop()
    await bus.stop()
    
    return deliveries, deaths

async def main():
    # 1. Baseline
    b_del, b_dead = await run_scenario("Baseline", RandomBaselineAgent)
    
    # 2. Smart
    s_del, s_dead = await run_scenario("Smart", WarehouseAgent)
    
    # Comparison
    print("\n" + "="*40)
    print(" BASELINE COMPARISON REPORT ")
    print("="*40)
    print(f"Baseline (Random): {b_del} Del, {b_dead} Deaths")
    print(f"Smart (Heuristic): {s_del} Del, {s_dead} Deaths")
    
    if s_del > b_del:
        imp = "Infinite" if b_del == 0 else f"{(s_del/b_del):.1f}x"
        print(f"Improvement: {imp} throughput gain.")
    else:
        print("WARNING: Smart agent underperformed baseline!")

if __name__ == "__main__":
    asyncio.run(main())
