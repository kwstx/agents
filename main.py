import asyncio
import logging
from utils.message_bus import MessageBus
from agents.prototypes import PingAgent, PongAgent, LoggerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_simulation():
    # 1. Initialize Bus
    bus = MessageBus()
    await bus.start()

    # 2. Create Agents
    pinger = PingAgent("Pinger-01", bus)
    ponger = PongAgent("Ponger-01", bus)
    logger = LoggerAgent("Logger-01", bus)

    # 3. Start Agents
    await pinger.start()
    await ponger.start()
    await logger.start()

    # 4. Trigger Action
    print("Starting simulation... Press Ctrl+C to stop.")
    await pinger.add_task("start_pinging")

    # 5. Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Stopping simulation...")
    finally:
        await pinger.stop()
        await ponger.stop()
        await logger.stop()
        await bus.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        pass

