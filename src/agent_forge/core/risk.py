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
    def __init__(self, latency_threshold: float = 1.0):
        self.agent_risk: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []
        self.latency_threshold = latency_threshold
        
    def record_violations(self, agent_id: str, violations: List[Dict[str, Any]]):
        if not violations:
            return
            
        current_score = self.agent_risk.get(agent_id, 0.0)
        
        for v in violations:
            rule = v.get("rule", "")
            duration = v.get("step_duration", 0.0)
            
            # 1. Base Impact
            impact = 10.0
            if "NEGATIVE" in rule:
                impact = 60.0
            elif "LOW" in rule:
                impact = 30.0
            elif "DEGRADED" in rule:
                impact = 10.0
            elif "BATTERY" in rule or "SOLVENCY" in rule:
                impact = 50.0 # Default fallback
            elif "BOUNDARY" in rule:
                impact = 20.0
                
            # 2. Causality Detection (Did latency cause this?)
            is_latency_correlated = duration > self.latency_threshold
            
            current_score += impact
            
            # Evidence Anchors: Lossless technical receipts
            evidence = [
                {
                    "signal_type": "STEP_DURATION",
                    "measured_value": duration,
                    "unit": "seconds",
                    "confidence_interval": 1.0
                }
            ]
            
            event = {
                "timestamp": time.time(),
                "agent_id": agent_id,
                "violation": v,
                "impact": impact,
                "step_duration": duration,
                "is_latency_correlated": is_latency_correlated,
                "evidence_anchors": evidence,
                "new_score": current_score,
                "causal_chain": []
            }
            
            if is_latency_correlated:
                msg = f"CRITICAL: Resource failure ({rule}) correlated with {duration:.2f}s latency injection."
                event["causal_chain"].append(msg)
                logger.warning(f"[CAUSALITY] {msg}")
            
            self.history.append(event)
            
        self.agent_risk[agent_id] = current_score
        logger.info(f"[RISK] Agent {agent_id} risk score increased to {current_score} ({self.get_risk_level(agent_id).value})")
        
    def get_risk_level(self, agent_id: str) -> RiskLevel:
        score = self.agent_risk.get(agent_id, 0.0)
        if score >= 100:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 20:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
        
    def reset(self):
        self.agent_risk = {}
        self.history = []

