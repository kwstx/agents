import asyncio
from typing import Any
from agent_forge.agents.base_agent import BaseAgent
from agent_forge.utils.message_bus import Message

class PingAgent(BaseAgent):
    async def process_task(self, task: Any):
        # Determine what to do based on task content
        if task == "start_pinging":
            self.running = True
            asyncio.create_task(self._ping_loop())

    async def _ping_loop(self):
        while self.running:
            await self.send_message("ping", "Ping!")
            await asyncio.sleep(2)  # Ping every 2 seconds

class PongAgent(BaseAgent):
    async def setup(self):
        self.message_bus.subscribe("ping", self.receive_message)

    async def receive_message(self, message: Message):
        await super().receive_message(message)
        if message.topic == "ping":
            self.logger.info(f"Received ping from {message.sender}, responding...")
            # Simulate some work
            await self.add_task(f"respond_to_{message.sender}")

    async def process_task(self, task: Any):
        if str(task).startswith("respond_to_"):
            target = task.split("_")[-1]
            await self.send_message("pong", f"Pong to {target}!")

class LoggerAgent(BaseAgent):
    async def setup(self):
        # Subscribe to all topics? In our simple bus, we don't have wildcard yet,
        # so let's subscribe to known topics for now.
        self.message_bus.subscribe("ping", self.receive_message)
        self.message_bus.subscribe("pong", self.receive_message)

    async def receive_message(self, message: Message):
        # Log everything to a file or special output
        self.logger.info(f"[GLOBAL LOG] {message.timestamp} | {message.sender} -> {message.topic}: {message.payload}")

    async def process_task(self, task: Any):
        pass
