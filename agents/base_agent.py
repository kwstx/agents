import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from utils.message_bus import MessageBus, Message

class BaseAgent(ABC):
    def __init__(self, agent_id: str, message_bus: MessageBus, log_dir: str = "logs"):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.state: Dict[str, Any] = {
            "status": "idle",
            "goals": [],
            "memory": {},
            "last_active": None
        }
        self.running = False
        
        # Setup specific logger for this agent
        self.logger = logging.getLogger(f"Agent.{agent_id}")
        self.logger.setLevel(logging.INFO)
        # File handler could be added here for individual agent logs
        
    async def start(self):
        """Starts the agent's main loop."""
        self.running = True
        self.state["status"] = "active"
        self.state["last_active"] = datetime.now()
        self.logger.info(f"Agent {self.agent_id} starting...")
        
        # Start processing tasks
        asyncio.create_task(self._process_tasks())
        
        await self.setup()

    async def stop(self):
        """Stops the agent."""
        self.running = False
        self.state["status"] = "stopped"
        self.logger.info(f"Agent {self.agent_id} stopping...")
        await self.teardown()

    async def setup(self):
        """Optional setup hook for subclasses."""
        pass

    async def teardown(self):
        """Optional teardown hook for subclasses."""
        pass

    async def receive_message(self, message: Message):
        """Handler implementation to be passed to MessageBus subscription."""
        # By default, specific agents should override or register specific handlers
        # This is a generic catch-all hooks
        self.log_activity("message_received", {"topic": message.topic, "sender": message.sender})

    async def send_message(self, topic: str, payload: Any):
        """Wrapper to publish messages."""
        await self.message_bus.publish(topic, self.agent_id, payload)
        self.log_activity("message_sent", {"topic": topic, "payload": payload})

    async def add_task(self, task: Any):
        """Adds a task to the agent's queue."""
        await self.task_queue.put(task)
        self.log_activity("task_added", {"task": str(task)})

    async def _process_tasks(self):
        """Internal loop to process tasks from the queue."""
        while self.running:
            try:
                # Wait for task with a timeout to allow checking self.running occasionally
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                self.state["status"] = "working"
                self.log_activity("task_started", {"task": str(task)})
                
                # Execute task
                result = await self.process_task(task)
                
                self.task_queue.task_done()
                self.state["status"] = "active"
                self.state["last_active"] = datetime.now()
                self.log_activity("task_completed", {"task": str(task)})
                
                # Save Checkpoint
                self.save_checkpoint(task, result)
                
            except Exception as e:
                self.logger.error(f"Error processing task: {e}")
                self.log_activity("task_error", {"error": str(e)})

    @abstractmethod
    async def process_task(self, task: Any):
        """Abstract method to define how to handle a task."""
        pass

    def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """ centralized logging for tracking agent behavior."""
        # In a real system, this might write to a structured log file or DB
        self.logger.info(f"[{activity_type}] {details}")

    def save_checkpoint(self, task: Any, result: Any = None):
        """Saves a debuggable checkpoint to disk."""
        import json
        import os
        
        checkpoint_dir = f"logs/checkpoints/{self.agent_id}"
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{checkpoint_dir}/{timestamp}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "state": str(self.state), # Simple stringify for MVP
            "task": str(task),
            "result": str(result)
        }
        
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
