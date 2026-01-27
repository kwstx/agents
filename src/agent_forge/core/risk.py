from enum import Enum
from typing import Dict, List, Any
import time
import logging

logger = logging.getLogger("RiskMonitor")

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskMonitor:
    def __init__(self):
        self.agent_risk: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []
        
    def record_violations(self, agent_id: str, violations: List[Dict[str, Any]]):
        if not violations:
            # Optional: Decay risk over time if no violations?
            # For now, we only accumulate.
            return
            
        current_score = self.agent_risk.get(agent_id, 0.0)
        
        for v in violations:
            # Simple weighting logic
            rule = v.get("rule", "")
            impact = 10.0
            
            # Example weights
            if "BATTERY" in rule:
                impact = 40.0 # High impact
            elif "BOUNDARY" in rule:
                impact = 30.0 # Medium impact
            
            current_score += impact
            
            self.history.append({
                "timestamp": time.time(),
                "agent_id": agent_id,
                "violation": v,
                "impact": impact,
                "new_score": current_score
            })
            
        self.agent_risk[agent_id] = current_score
        logger.info(f"[RISK] Agent {agent_id} risk score increased to {current_score} ({self.get_risk_level(agent_id).value})")
        
    def get_risk_level(self, agent_id: str) -> RiskLevel:
        score = self.agent_risk.get(agent_id, 0.0)
        if score >= 100:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
        
    def reset(self):
        self.agent_risk = {}
        self.history = []
