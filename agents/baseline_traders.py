import random
import asyncio
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

class HoldAgent(BaseAgent):
    """Does nothing. Effectively holds cash/inventory."""
    async def process_task(self, task):
        # Acknowledge but do nothing
        self.logger.info("HoldAgent: Holding position. No action.")
        return {"action": "HOLD"}

class BuyAgent(BaseAgent):
    """Aggressively Buys."""
    async def process_task(self, task):
        # Simple logic: Buy @ 100 or Price in task
        price = 100.0
        if isinstance(task, dict) and 'price' in task:
            price = task['price']
            
        action = {
            "type": "LIMIT",
            "side": "BUY",
            "price": price,
            "quantity": 10,
            "id": f"buy_{random.randint(1000,9999)}",
            "agent_id": self.agent_id
        }
        # In a real system, we'd send this to the Execution Engine topic.
        # For tests, we might return it or publish it.
        # Let's assume we publish to 'order_entry'
        await self.send_message("order_entry", action)
        return {"action": "BUY_SENT"}

class RandomAgent(BaseAgent):
    """Randomly Buys, Sells, or Cancels."""
    async def process_task(self, task):
        action_type = random.choice(["BUY", "SELL", "CANCEL", "HOLD"])
        
        if action_type == "HOLD":
            return {"action": "HOLD"}
            
        if action_type == "CANCEL":
            # Needs an ID to cancel. For now just generating a dummy one or skipping
            return {"action": "CANCEL_SKIPPED"}
            
        price = 100.0 + random.uniform(-5, 5)
        action = {
            "type": "LIMIT",
            "side": action_type,
            "price": round(price, 2),
            "quantity": random.randint(1, 10),
            "id": f"rnd_{random.randint(1000,9999)}",
            "agent_id": self.agent_id
        }
        await self.send_message("order_entry", action)
        return {"action": f"{action_type}_SENT"}
