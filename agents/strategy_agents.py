from typing import Dict, Any, List
from .base_agent import BaseAgent
import numpy as np

class StrategyAgent(BaseAgent):
    def __init__(self, agent_id: str, start_cash: float, message_bus=None):
        super().__init__(agent_id, message_bus=message_bus)
        self.agent_id = agent_id
        # We don't track portfolio internally, we trust the Env/wrapper to tell us, 
        # or we just blindly emit orders for this simple test.
        self.last_price = 100.0
        self.price_history = []

    async def process_task(self, task: Any) -> Dict[str, Any]:
        # Task is essentially "Market Update" -> "Action"
        # For simplicity in this manual test loop, we'll likely call a method directly 
        # or wrap the update in a task structure.
        # Let's assume the test script calls `decide(obs)`.
        pass

    def decide(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous decision method for the manual test loop.
        """
        mid = obs['mid_price']
        self.price_history.append(mid)
        if len(self.price_history) > 20:
            self.price_history.pop(0)
            
        action = self._strategy_logic(obs)
        self.last_price = mid
        return action

    def _strategy_logic(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        return {'type': 'HOLD', 'id': 'noop', 'agent_id': self.agent_id}

class MomentumTrader(StrategyAgent):
    def __init__(self, agent_id: str, start_cash: float, threshold: float = 0.5, message_bus=None):
        super().__init__(agent_id, start_cash, message_bus=message_bus)
        self.threshold = threshold

    def _strategy_logic(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        mid = obs['mid_price']
        change = mid - self.last_price
        
        # If price rose significantly, BUY (Herding)
        if change > self.threshold:
            # Join the rally
            price = mid + 0.1 # Aggressive
            return {'type': 'LIMIT', 'side': 'BUY', 'price': price, 'quantity': 10, 'id': f'{self.agent_id}_mom_b', 'agent_id': self.agent_id}
        
        # If price fell significantly, SELL (Panic)
        elif change < -self.threshold:
            price = mid - 0.1 # Dump
            return {'type': 'LIMIT', 'side': 'SELL', 'price': price, 'quantity': 10, 'id': f'{self.agent_id}_mom_s', 'agent_id': self.agent_id}
            
        return {'type': 'HOLD', 'id': 'noop', 'agent_id': self.agent_id}

class MeanReversionTrader(StrategyAgent):
    def __init__(self, agent_id: str, start_cash: float, window: int = 10, deviation: float = 1.0, message_bus=None):
        super().__init__(agent_id, start_cash, message_bus=message_bus)
        self.window = window
        self.deviation = deviation

    def _strategy_logic(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        if len(self.price_history) < self.window:
            return {'type': 'HOLD', 'id': 'noop', 'agent_id': self.agent_id}
            
        avg = np.mean(self.price_history[-self.window:])
        mid = obs['mid_price']
        
        # If Price > Avg + Dev, SELL (Overvalued)
        if mid > avg + self.deviation:
            price = mid - 0.1
            return {'type': 'LIMIT', 'side': 'SELL', 'price': price, 'quantity': 5, 'id': f'{self.agent_id}_mr_s', 'agent_id': self.agent_id}
            
        # If Price < Avg - Dev, BUY (Undervalued)
        elif mid < avg - self.deviation:
            price = mid + 0.1
            return {'type': 'LIMIT', 'side': 'BUY', 'price': price, 'quantity': 5, 'id': f'{self.agent_id}_mr_b', 'agent_id': self.agent_id}
            
        return {'type': 'HOLD', 'id': 'noop', 'agent_id': self.agent_id}
