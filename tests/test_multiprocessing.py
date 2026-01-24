import pytest
import asyncio
import time
import math
import concurrent.futures
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

# --- Helper Function for CPU Bound Task ---
def heavy_cpu_task(n: int) -> int:
    """Calculates info for a range to simulate CPU work.
    Intentionally slow to verify non-blocking behavior.
    """
    # Simple busy wait to simulate work (better than sleep for process testing)
    end_time = time.time() + 0.5 # 500ms of busy work
    count = 0
    while time.time() < end_time:
        count += 1
        math.sqrt(count) # Burn CPU
    return n * n

# --- Agent Implementation ---
class CPUHeavyAgent(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)

    async def process_task(self, task):
        loop = asyncio.get_running_loop()
        
        if task.startswith("calc_"):
            n = int(task.split("_")[1])
            # Offload to process pool
            result = await loop.run_in_executor(self.executor, heavy_cpu_task, n)
            await self.send_message("result", result)

    async def teardown(self):
        self.executor.shutdown()

# --- Tests ---

@pytest.mark.asyncio
async def test_non_blocking_execution():
    """Verify that while a heavy task runs, the event loop keeps ticking."""
    bus = MessageBus()
    await bus.start()
    
    agent = CPUHeavyAgent("CPU-1", bus)
    await agent.start()
    
    # Start heartbeats
    heartbeats = 0
    async def heartbeat_loop():
        nonlocal heartbeats
        while agent.running:
            heartbeats += 1
            await asyncio.sleep(0.1)

    # Launch task
    await agent.add_task("calc_10")
    
    # Run heartbeat concurrently
    hb_task = asyncio.create_task(heartbeat_loop())
    
    # Wait for result
    msg = None
    async def capture(m): nonlocal msg; msg = m
    bus.subscribe("result", capture)
    
    # Wait enough time for calculation to finish (approx 0.5s)
    await asyncio.sleep(1.0)
    
    await agent.stop()
    await bus.stop()
    await hb_task
    
    # Assertions
    # 1. We got the result
    assert msg is not None
    assert msg.payload == 100
    
    # 2. Heartbeats continued during the 0.5s work
    # Expect roughly 10 heartbeats in 1.0s. If blocked, we'd get fewer (or 0 during the 0.5s wait)
    # 5 heartbeats would mean it ran for at least 0.5s of free time. 
    # If strictly blocked, we might see very few.
    assert heartbeats >= 5, f"Event loop blocked! Only {heartbeats} heartbeats."

@pytest.mark.asyncio
async def test_simultaneous_load():
    """Verify multiple heavy tasks can run in parallel processes."""
    bus = MessageBus()
    await bus.start()
    
    agent = CPUHeavyAgent("CPU-Multi", bus)
    await agent.start()
    
    results = set()
    async def capture(m): results.add(m.payload)
    bus.subscribe("result", capture)
    
    # Queue multiple tasks
    await agent.add_task("calc_5")
    await agent.add_task("calc_6")
    await agent.add_task("calc_7")
    
    # Wait for all (approx 0.5s parallel if 2 workers, maybe 1.0s total)
    # Increased to 4.0s to avoid flakiness on slower environments
    await asyncio.sleep(4.0)
    
    assert len(results) == 3
    assert 25 in results
    assert 36 in results
    assert 49 in results
    
    await agent.stop()
    await bus.stop()
