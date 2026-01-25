from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid

@dataclass
class BaseTask:
    """
    Standard interface for all tasks in the system.
    Plugins must accept tasks that conform to this protocol.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "generic"
    content: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """
        Validates the task structure.
        """
        if not self.id:
            raise ValueError("Task ID cannot be empty.")
        if not self.type:
            raise ValueError("Task type cannot be empty.")
        return True
