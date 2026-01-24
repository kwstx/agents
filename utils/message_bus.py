import asyncio
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import inspect  # Added for inspection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MessageBus")

@dataclass
class Message:
    topic: str
    sender: str
    payload: Any
    timestamp: datetime = datetime.now()

class MessageBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Message], Any]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self):
        """Starts the message processing loop."""
        self._running = True
        logger.info("MessageBus started.")
        asyncio.create_task(self._process_queue())

    async def stop(self):
        """Stops the message bus."""
        self._running = False
        logger.info("MessageBus stopped.")

    def subscribe(self, topic: str, handler: Callable[[Message], Any]):
        """Subscribes a handler callback to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to '{topic}'")

    async def publish(self, topic: str, sender: str, payload: Any):
        """Publishes a message to a topic."""
        message = Message(topic=topic, sender=sender, payload=payload, timestamp=datetime.now())
        await self._queue.put(message)
        logger.debug(f"Published to '{topic}' from '{sender}'")

    async def _process_queue(self):
        """Internal loop to process messages from the queue."""
        while self._running:
            try:
                message = await self._queue.get()
                if message.topic in self._subscribers:
                    for handler in self._subscribers[message.topic]:
                        try:
                            # Invoke handler, check if it's a coroutine
                            if inspect.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception as e:
                            logger.error(f"Error handling message on topic '{message.topic}': {e}")
                
                # Also handle wildcard subscriptions if we implement them later
                
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
