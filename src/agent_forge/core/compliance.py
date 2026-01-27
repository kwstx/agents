from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("Compliance")

@dataclass
class Violation:
    agent_id: str
    rule_id: str
    message: str
    context: Dict[str, Any]

class ComplianceAuditor:
    def __init__(self, grid_size: int = 10):
        self.grid_size = grid_size
        self.violations: List[Violation] = []

    def audit_state(self, agent_id: str, state: Dict[str, Any]) -> List[Violation]:
        """
        Checks a single agent state for invariant violations.
        Returns a list of violations found.
        """
        current_violations = []
        
        # 1. Physics: Battery Check
        # Invariant: Battery must be >= 0.0
        # Allow 0.0 (Dead), but not negative.
        battery = state.get("battery", 0.0)
        if battery < 0.0:
            # We allow a tiny epsilon for float precision issues if needed, but strictly < 0 is usually a bug logic
            v = Violation(
                agent_id=agent_id,
                rule_id="PHYSICS_BATTERY_NEGATIVE",
                message=f"Battery level negative: {battery}",
                context={"battery": battery}
            )
            current_violations.append(v)
            
        # 2. Boundary: Position Check
        # Invariant: 0 <= x < size, 0 <= y < size
        pos = state.get("position")
        if pos:
            x, y = pos
            if not (0 <= x < self.grid_size and 0 <= y < self.grid_size):
                v = Violation(
                    agent_id=agent_id,
                    rule_id="BOUNDARY_OUT_OF_BOUNDS",
                    message=f"Position {pos} is out of grid bounds (0-{self.grid_size-1})",
                    context={"position": pos, "grid_size": self.grid_size}
                )
                current_violations.append(v)
                
        # Log Violations
        for v in current_violations:
            logger.error(f"[AUDIT VIOLATION] Agent:{v.agent_id} Rule:{v.rule_id} Msg:{v.message}")
            self.violations.append(v)
            
        return current_violations

    def reset(self):
        self.violations = []
