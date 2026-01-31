from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class FaultType(Enum):
    LOGIC_DEFECT = "LOGIC_DEFECT"
    ENVIRONMENTAL_STRESS = "ENVIRONMENTAL_STRESS"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    GOVERNANCE_BREACH = "GOVERNANCE_BREACH"
    UNDETERMINED = "UNDETERMINED"

@dataclass
class Agent:
    """The Liable Actor in the system."""
    id: str
    type: str # e.g., 'Logistics-Bot', 'Trading-Agent'
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Asset:
    """The Exposed Value at risk."""
    id: str
    type: str # e.g., 'Inventory-Item', 'Cash-Balance'
    valuation_usd: float

@dataclass
class Goal:
    """The Contractual Objective or Mission."""
    id: str
    description: str
    criticality: int # 1-10 (1=Low, 10=Mission Critical)
    impact_description: str # Business impact if goal fails

@dataclass
class GovernanceStandard:
    """The Rulebook/Compliance standard applied to the agent."""
    name: str
    version: str
    rules: List[str]

@dataclass
class EvidenceAnchor:
    """A lossless technical signal justifying a forensic claim."""
    timestamp: float
    signal_type: str # e.g., 'LATENCY_MS', 'MEMORY_DELTA'
    measured_value: Any
    unit: str
    confidence_interval: float = 1.0 # 0.0 to 1.0
