from typing import Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger("FinancialRisk")

class RiskViolation(Enum):
    POSITION_LIMIT = "POSITION_LIMIT_EXCEEDED"
    DRAWDOWN_LIMIT = "MAX_DRAWDOWN_EXCEEDED"

class FinancialRiskMonitor:
    def __init__(self, max_position: int = 100, max_drawdown: float = 0.2):
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.peak_equity: Dict[str, float] = {}

    def check_risk(self, agent_id: str, portfolio: Dict[str, float], current_price: float) -> List[Dict[str, Any]]:
        violations = []
        
        cash = portfolio.get('cash', 0.0)
        inventory = portfolio.get('inventory', 0)
        
        # 1. Position Limit
        if abs(inventory) > self.max_position:
            violations.append({
                "type": RiskViolation.POSITION_LIMIT.value,
                "details": f"Inventory {inventory} exceeds limit {self.max_position}"
            })

        # 2. Drawdown
        equity = cash + (inventory * current_price)
        
        # Update Peak
        if agent_id not in self.peak_equity:
            self.peak_equity[agent_id] = equity
        else:
            self.peak_equity[agent_id] = max(self.peak_equity[agent_id], equity)
            
        peak = self.peak_equity[agent_id]
        drawdown = 0.0
        if peak > 0:
            drawdown = (peak - equity) / peak
            
        if drawdown > self.max_drawdown:
            violations.append({
                "type": RiskViolation.DRAWDOWN_LIMIT.value,
                "details": f"Drawdown {drawdown:.2%} exceeds limit {self.max_drawdown:.2%}"
            })
            
        return violations

class SystemicRiskMonitor:
    def __init__(self, vol_window: int = 20, stress_threshold: float = 2.0):
        self.prices = []
        self.vol_window = vol_window
        self.stress_threshold = stress_threshold
        # Agent Activity: AgentID -> Volume
        self.agent_volume: Dict[str, float] = {}

    def update(self, obs: Dict[str, Any], trades: List[Dict[str, Any]]):
        mid = obs['mid_price']
        self.prices.append(mid)
        if len(self.prices) > self.vol_window:
            self.prices.pop(0)
            
        # Track Volume
        for t in trades:
            b = t['buy_agent_id']
            s = t['sell_agent_id']
            qty = t['quantity']
            self.agent_volume[b] = self.agent_volume.get(b, 0) + qty
            self.agent_volume[s] = self.agent_volume.get(s, 0) + qty

    def detect_stress(self) -> Dict[str, Any]:
        """
        Returns stress report if volatility is high.
        """
        if len(self.prices) < 5:
            return {}
            
        import numpy as np
        vol = np.std(self.prices)
        
        if vol > self.stress_threshold:
            # Attribution: Who traded the most?
            sorted_agents = sorted(self.agent_volume.items(), key=lambda x: x[1], reverse=True)
            top_contributors = sorted_agents[:3]
            
            return {
                "status": "HIGH_VOLATILITY",
                "volatility": vol,
                "top_contributors": top_contributors
            }
            
        return {"status": "NORMAL", "volatility": vol}
