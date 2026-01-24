import asyncio
import time
import tracemalloc
import statistics
import random
import os
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.interaction_logger import InteractionLogger

# Config
COUNTS = [10, 50, 100]
STEPS_PER_AGENT = 20
DB_PATH = "stress_test.db"
LOG_FILE = "stress_test.jsonl"

async def run_agent_task(engine, agent_id, latencies):
    actions = ["RIGHT", "UP", "LEFT", "DOWN"]
    for _ in range(STEPS_PER_AGENT):
        action = random.choice(actions)
        
        start = time.time()
        await engine.perform_action(agent_id, action)
        end = time.time()
        
        latencies.append(end - start)
        # Small sleep to simulate minimal think time (non-blocking)
        await asyncio.sleep(random.uniform(0.001, 0.005))

async def stress_test():
    print("Starting Stress Test...")
    tracemalloc.start()
    
    # Setup
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    
    env = GridWorld(size=10) # Bigger world for more agents
    logger = InteractionLogger(DB_PATH, LOG_FILE)
    # No artificial stress in engine, we want to measure SYSTEM stress
    engine = SimulationEngine(env, logger, stress_config={})
    
    for count in COUNTS:
        print(f"\n--- Testing with {count} Concurrent Agents ---")
        
        latencies = []
        tasks = []
        
        start_time = time.time()
        current_mem_start, peak_mem_start = tracemalloc.get_traced_memory()
        
        for i in range(count):
            agent_id = f"Agent-{count}-{i}"
            tasks.append(run_agent_task(engine, agent_id, latencies))
            
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        current_mem_end, peak_mem_end = tracemalloc.get_traced_memory()
        
        # Metrics
        total_time = end_time - start_time
        total_actions = count * STEPS_PER_AGENT
        throughput = total_actions / total_time
        avg_latency = statistics.mean(latencies)
        p99_latency = statistics.quantiles(latencies, n=100)[98]
        
        print(f"Total Time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} actions/sec")
        print(f"Latency: Avg {avg_latency*1000:.2f}ms | P99 {p99_latency*1000:.2f}ms")
        print(f"Memory Growth: {(current_mem_end - current_mem_start)/1024:.2f} KB")
        print(f"Peak Memory: {peak_mem_end/1024/1024:.2f} MB")
        
    tracemalloc.stop()
    
    # Cleanup
    try:
        os.remove(DB_PATH)
        os.remove(LOG_FILE)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(stress_test())
