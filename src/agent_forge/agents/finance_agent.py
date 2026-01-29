from .base_agent import BaseAgent

class FinanceAgent(BaseAgent):
    """
    A simple example agent specialized for 'finance' tasks (mock implementation).
    """
    def __init__(self, agent_id: str, message_bus=None, risk_tolerance: float = 0.5):
        super().__init__(agent_id, message_bus)
        self.risk_tolerance = risk_tolerance
        self.balance = 10000.0

    def decide(self, observation):
        """
        Simple logic: if market is 'bullish', buy; if 'bearish', sell.
        """
        market_sentiment = observation.get("sentiment", "neutral")
        price = observation.get("price", 100.0)

        if market_sentiment == "bullish" and self.balance > price:
            return {"action": "buy", "amount": 1}
        elif market_sentiment == "bearish":
             return {"action": "sell", "amount": 1}
        return {"action": "hold"}

    async def process_task(self, task):
        """
        Handle a task. For finance agent, maybe analyze a report or trade.
        """
        print(f"FinanceAgent processing task: {task}")
        # Example logic: if task is 'analyze_market', run decide logic
        if isinstance(task, dict) and task.get("type") == "market_update":
            return self.decide(task.get("data", {}))
        return {"status": "completed", "task": task}
