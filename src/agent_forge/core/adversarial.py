import random
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger("Adversarial")

@dataclass
class AdversarialConfig:
    enabled: bool = False
    jitter_rate: float = 0.0          # Probability of applying jitter
    latency_range: tuple = (0.0, 0.0) # (min, max) seconds
    drop_rate: float = 0.0            # Probability of dropping an action (Process Failure)
    network_partition: bool = False   # If True, all comms blocked
    
class AdversarialMiddleware:
    def __init__(self, config: AdversarialConfig):
        self.config = config
        
    async def intercept_action(self, agent_id: str, action: str) -> bool:
        """
        Intercepts an agent active action.
        Returns False if action should be dropped/failed.
        """
        if not self.config.enabled:
            return True
            
        # 1. Action Dropping (Simulation of Process Crash or Message Loss)
        if self.config.drop_rate > 0:
            if random.random() < self.config.drop_rate:
                logger.warning(f"[CHAOS] Dropping action '{action}' from {agent_id}")
                return False
                
        # 2. Latency Injection (Simulation of Network Lag / Slow Compute)
        if self.config.jitter_rate > 0 and self.config.latency_range[1] > 0:
            if random.random() < self.config.jitter_rate:
                delay = random.uniform(*self.config.latency_range)
                # logger.debug(f"[CHAOS] Injecting {delay:.2f}s latency for {agent_id}")
                await asyncio.sleep(delay)
                
        return True

    def update_config(self, new_config: Dict[str, Any]):
        """Runtime update of chaos params"""
        for k, v in new_config.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        logger.info(f"Adversarial Config Updated: {self.config}")
