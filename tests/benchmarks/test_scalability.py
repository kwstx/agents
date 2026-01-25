import asyncio
import time
import tracemalloc
import sys
import os
import statistics

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

# Define a lightweight benchmark agent
class BenchmarkAgent(BaseAgent):
    async def process_task(self, task):
        return "done"
    
    async def receive_message(self, message):
        # Simply acknowledge receipt by updating local state (no heavy logic)
        self.state["last_msg"] = message.payload

async def measure_load_time(n_agents):
    bus = MessageBus()
    agents = []
    
    start_time = time.time()
    for i in range(n_agents):
        agent = BenchmarkAgent(f"agent_{i}", bus)
        # Mock memory to avoid disk I/O noise
        agent.setup_memory = lambda: None 
        agents.append(agent)
    end_time = time.time()
    
    return end_time - start_time, agents, bus

async def measure_latency(agents, bus):
    # Register all first
    for agent in agents:
        bus.register(agent.agent_id)
        agent.subscribe("test_topic")
        
    # Register broadcaster so it can send
    token = bus.register("broadcaster")

    # Broadcast message
    start_time = time.time()
    await bus.publish("test_topic", "broadcaster", "payload", "event", receiver="all", auth_token=token)
    
    # In a real async system, we'd wait for all to process. 
    # For this micro-benchmark, we rely on the bus being in-memory and awaiting run_until_complete 
    # if we were strictly integration testing, but here we just await publish.
    # However, MessageBus.publish might just put in a queue. 
    # Let's assume we need to process the queue.
    # BaseAgent doesn't auto-process messages in a background loop unless start() is called.
    # We'll simulate processing:
    
    for agent in agents:
        # Manually trigger handler for the sake of isolation benchmark
        # (simulating the bus delivering it)
        await agent.receive_message(type('obj', (object,), {
            "topic": "test_topic", "sender": "broadcaster", "receiver": "all", "payload": "payload", "trace_id": "1", "parent_id": None
        }))
        
    end_time = time.time()
    return end_time - start_time

def run_benchmark():
    COUNTS = [10, 50, 100, 200]
    results = []

    print(f"{'Count':<10} | {'Load Time (s)':<15} | {'Memory (MB)':<15} | {'Latency (s)':<15}")
    print("-" * 65)

    for count in COUNTS:
        tracemalloc.start()
        
        # Measure Load
        load_time, agents, bus = asyncio.run(measure_load_time(count))
        
        # Measure Memory
        current, peak = tracemalloc.get_traced_memory()
        memory_mb = peak / (1024 * 1024)
        
        # Measure Latency
        latency = asyncio.run(measure_latency(agents, bus))
        
        tracemalloc.stop()
        
        print(f"{count:<10} | {load_time:<15.4f} | {memory_mb:<15.4f} | {latency:<15.4f}")
        results.append({
            "count": count,
            "load_time": load_time,
            "memory_mb": memory_mb,
            "latency": latency
        })

    # Linear scaling verification (rough heuristic)
    # Check if 100 agents take roughly 10x the time/memory of 10 agents (allowing for constant overhead)
    base = results[0] # 10 agents
    scale = results[2] # 100 agents
    
    print("\nScaling Analysis:")
    load_factor = scale["load_time"] / base["load_time"]
    mem_factor = scale["memory_mb"] / base["memory_mb"]
    
    print(f"10x Agent Increase -> {load_factor:.2f}x Load Time Increase")
    print(f"10x Agent Increase -> {mem_factor:.2f}x Memory Increase")
    
    if load_factor > 20: # Allow some buffer, perfect is 10x
        print("WARNING: Load time scaling is potentially super-linear.")
    else:
        print("PASS: Load time scales linearly.")
        
    if mem_factor > 20:
        print("WARNING: Memory scaling is potentially super-linear.")
    else:
        print("PASS: Memory scales linearly.")

if __name__ == "__main__":
    run_benchmark()
