import asyncio
import logging
import random
import os
from datetime import datetime
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

# Setup File Logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{log_dir}/stress_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("StressTest")

# --- Special Test Agents ---

class LaggyAgent(BaseAgent):
    """Simulates network latency by sleeping before processing."""
    async def process_task(self, task):
        delay = random.uniform(0.1, 0.5)
        await asyncio.sleep(delay)
        await self.send_message("laggy_response", f"Processed {task} after {delay:.2f}s")
        self.logger.info(f"Finished {task} with delay {delay:.2f}s")

class BurstyAgent(BaseAgent):
    """Sends a burst of messages."""
    async def process_task(self, task):
        if task.startswith("burst"):
            count = int(task.split("_")[1])
            for i in range(count):
                await self.send_message("burst_topic", f"Burst message {i}")
                # Minimal yielding to allow things to queue up
                if i % 10 == 0:
                    await asyncio.sleep(0.01)

class FragileAgent(BaseAgent):
    """Randomly fails processing tasks."""
    async def process_task(self, task):
        if random.random() < 0.3:
            raise ValueError("Random simulated failure!")
        await self.send_message("fragile_success", f"Survived {task}")

# --- Verification Logic ---

async def run_stress_test():
    bus = MessageBus()
    await bus.start()

    logger.info("Initializing Agents...")
    laggy = LaggyAgent("Laggy", bus)
    bursty = BurstyAgent("Bursty", bus)
    fragile = FragileAgent("Fragile", bus)

    await laggy.start()
    await bursty.start()
    await fragile.start()

    # Trackers
    received_count = 0
    errors_caught = 0

    async def global_spy(message):
        nonlocal received_count
        received_count += 1
        
    bus.subscribe("laggy_response", global_spy)
    bus.subscribe("burst_topic", global_spy)
    bus.subscribe("fragile_success", global_spy)

    logger.info("--- Starting Latency Test ---")
    for i in range(5):
        await laggy.add_task(f"UserReq_{i}")
    
    logger.info("--- Starting Burst Test ---")
    await bursty.add_task("burst_50") # 50 messages

    logger.info("--- Starting Random Failure Test ---")
    for i in range(10):
        await fragile.add_task(f"Risk_{i}")

    # Wait for processing
    logger.info("Waiting for agents to clear queues...")
    await asyncio.sleep(5) 

    logger.info(f"Total Messages Received on Bus Subscriptions: {received_count}")
    
    # Assertions / Checks
    # 5 laggy responses + 50 burst messages + ~7 fragile successes (approx)
    # Total roughly 62 messages.
    
    if received_count < 55:
        logger.error("Message count too low! Potential loss.")
    else:
        logger.info("Message count looks healthy.")

    await laggy.stop()
    await bursty.stop()
    await fragile.stop()
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_stress_test())
