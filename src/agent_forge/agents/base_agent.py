import asyncio
import logging
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from agent_forge.utils.message_bus import MessageBus, Message

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
        
        
        # Load settings for storage path if available, else default
        # We'll initialize explicit memory in setup() or lazy load to avoid pickling issues if passed around
        self.memory_module = None 
        self._auth_token = None # Security token
        self.active_subscriptions = set() # Track topics we subscribe to

    async def start(self):
        """Starts the agent's main loop."""
        self.running = True
        self.state["status"] = "active"
        self.state["last_active"] = datetime.now()
        self.logger.info(f"Agent {self.agent_id} starting...")
        
        # Register with MessageBus
        self._auth_token = self.message_bus.register(self.agent_id)
        
        await self.setup_memory() # Ensure memory is ready
        
        # Start processing tasks
        asyncio.create_task(self._process_tasks())
        
        await self.setup()

    def subscribe(self, topic: str):
        """Subscribes the agent to a topic and tracks it for cleanup."""
        self.message_bus.subscribe(topic, self.receive_message)
        self.active_subscriptions.add(topic)

    async def setup_memory(self):
        """Initializes the persistent memory connection."""
        from utils.memory import Memory
        import yaml
        
        db_path = "data/memory.db"
        try:
            with open("config/settings.yaml", "r") as f:
                config = yaml.safe_load(f)
                if "storage" in config:
                    db_path = config["storage"].get("path", db_path)
        except Exception:
            pass # Use default
            
        self.memory_module = Memory(db_path=db_path)

    async def stop(self):
        """Stops the agent and cleans up subscriptions."""
        self.running = False
        self.state["status"] = "stopped"
        self.logger.info(f"Agent {self.agent_id} stopping...")
        
        # Cleanup subscriptions
        for topic in self.active_subscriptions:
            self.message_bus.unsubscribe(topic, self.receive_message)
        self.active_subscriptions.clear()
        
        await self.teardown()

    async def setup(self):
        """Optional setup hook for subclasses."""
        pass

    async def teardown(self):
        """Optional teardown hook for subclasses."""
        pass

    async def receive_message(self, message: Message):
        """Handler implementation to be passed to MessageBus subscription."""
        # STRICT Filtering: Ignore if not for me or all
        if message.receiver and message.receiver not in [self.agent_id, "all"]:
            return 
            
        # By default, specific agents should override or register specific handlers
        # This is a generic catch-all hooks
        # DEBUG PRINT
        # print(f"DEBUG: Agent {self.agent_id} received {message.topic} from {message.sender}")
        self.log_activity("message_received", {"topic": message.topic, "sender": message.sender})

    async def send_message(self, topic: str, payload: Any, message_type: str = "event", receiver: str = None, trace_id: str = None, parent_id: str = None):
        """Wrapper to publish messages."""
        await self.message_bus.publish(
            topic, 
            self.agent_id, 
            payload, 
            message_type, 
            receiver, 
            trace_id, 
            parent_id,
            auth_token=self._auth_token
        )
        self.log_activity("message_sent", {
            "topic": topic, 
            "payload": payload, 
            "type": message_type, 
            "receiver": receiver,
            "trace_id": trace_id,
            "parent_id": parent_id
        })

    async def reply(self, original_message: Message, payload: Any, message_type: str = "response"):
        """Helper to reply to a message, preserving the causal chain."""
        await self.send_message(
            topic=original_message.topic,
            payload=payload,
            message_type=message_type,
            receiver=original_message.sender,
            trace_id=original_message.trace_id, # Keep same conversation trace
            parent_id=original_message.trace_id # Point to parent
        )

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
                
                # Execute task with strict timeout
                try:
                    # Timeout default 5.0s, could be configurable per task
                    result = await asyncio.wait_for(self.process_task(task), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.error(f"Task execution timed out: {task}")
                    result = {"status": "failed", "error": "Execution Timed Out"}
                    # We continue the loop, agent survives
                
                self.task_queue.task_done()
                self.state["status"] = "active"
                self.state["last_active"] = datetime.now()
                self.log_activity("task_completed", {"task": str(task)})
                
                # Save Checkpoint
                self.save_checkpoint(task, result)
                
            except Exception as e:
                self.logger.error(f"Error processing task: {e}")
                self.log_activity("task_error", {"error": str(e)})

    async def process_task(self, task: Any):
        """
        Method to define how to handle a task.
        Implementation of 'process_task' is preferred.
        Falls back to 'perform' (legacy) with a warning.
        
        Args:
            task (BaseTask): The task to process.
        
        Returns:
            Any: The result of the task processing.
        """
        # Compatibility Layer for v1 agents
        if hasattr(self, 'perform') and callable(self.perform):
             self.logger.warning("DeprecationWarning: Agent implements legacy 'perform' method. Please migrate to 'process_task'.")
             # Handle async vs sync legacy perform
             if inspect.iscoroutinefunction(self.perform):
                 return await self.perform(task)
             else:
                 return self.perform(task)
                 
        raise NotImplementedError("Agent must implement 'process_task'.")

    def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """ centralized logging for tracking agent behavior."""
        # Log to standard python logger
        self.logger.info(f"[{activity_type}] {details}")
        
        # Log to persistent memory
        self.log_memory(activity_type, details)

    def log_memory(self, type: str, content: Any, sim_context: Optional[Dict] = None):
        """Logs content to the persistent memory store."""
        if self.memory_module:
            try:
                # Merge passed context with default status
                ctx = {"status": self.state.get("status")}
                if sim_context:
                    ctx.update(sim_context)
                    
                self.memory_module.add_memory(
                    agent_id=self.agent_id, 
                    type=type, 
                    content=content,
                    sim_context=ctx
                )
            except Exception as e:
                self.logger.error(f"Failed to write to memory: {e}")

    def recall_memories(self, limit: int = 50, filter_metadata: Dict[str, Any] = None) -> list:
        """
        Retrieves this agent's own memories.
        Strictly isolated: does not allow querying other agent IDs.
        """
        if not self.memory_module:
            return []
            
        try:
            return self.memory_module.query_memory(
                agent_id=self.agent_id, # Strict Isolation
                limit=limit,
                filter_metadata=filter_metadata
            )
        except Exception as e:
            self.logger.error(f"Failed to recall memory: {e}")
            return []

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
