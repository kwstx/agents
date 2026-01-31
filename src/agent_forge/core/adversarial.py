import random
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger("Adversarial")

@dataclass
class AdversarialConfig:
    enabled: bool = False
    seed: Optional[int] = None        # Random seed for determinism
    jitter_rate: float = 0.0          # Probability of applying jitter
    latency_range: tuple = (0.0, 0.0) # (min, max) seconds
    drop_rate: float = 0.0            # Probability of dropping an action
    network_partition: bool = False   # If True, all comms blocked
    
    # Profile Configs
    profile_name: str = "custom"      # custom, flaky_wifi, data_center_outage
    spike_chance: float = 0.05        # Prob of entering spike mode
    spike_multiplier: float = 10.0    # Latency multiplier during spike
    outage_interval: float = 30.0     # Seconds between outages
    outage_duration: float = 5.0      # Duration of outage

    def __post_init__(self):
        # Safety Boundaries
        self.jitter_rate = max(0.0, min(1.0, self.jitter_rate))
        self.drop_rate = max(0.0, min(1.0, self.drop_rate))
        self.spike_chance = max(0.0, min(1.0, self.spike_chance))
        
        # Ensure latency_range is valid
        if not isinstance(self.latency_range, tuple) or len(self.latency_range) != 2:
            self.latency_range = (0.0, 0.0)
        
        low, high = self.latency_range
        self.latency_range = (max(0.0, low), max(0.0, high))
        if self.latency_range[0] > self.latency_range[1]:
            self.latency_range = (self.latency_range[1], self.latency_range[0])

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

class AdversarialMiddleware:
    def __init__(self, config: AdversarialConfig):
        self.config = config
        self._rng = random.Random(config.seed) if config.seed is not None else random
        # Persistent state for profiles
        self.in_burst = False
        self.outage_end = 0.0
        self.next_outage = 0.0 # Will be initialized on first call if needed
        
    def _calculate_delay(self) -> float:
        """
        Internal logic to determine delay without sleeping.
        Used for testing and by intercept_action.
        """
        if not self.config.enabled:
            return 0.0
            
        delay = 0.0
        low, high = self.config.latency_range

        def sample_range(l, h):
            if h == float('inf'):
                return float('inf')
            return self._rng.uniform(l, h)
        
        # Profile: Flaky Wi-Fi (Bursty Spikes)
        if self.config.profile_name == "flaky_wifi":
            check = self._rng.random()
            if self.in_burst:
                if check < 0.3: # 30% chance to recover
                    self.in_burst = False
            else:
                if check < self.config.spike_chance:
                    self.in_burst = True
                    
            if self.in_burst:
                base = sample_range(low, high)
                delay = base * self.config.spike_multiplier
            else:
                delay = sample_range(low, high)

        # Profile: Data Center Outage (Sustained Blocking)
        elif self.config.profile_name == "data_center_outage":
            import time
            now = time.time()
            
            if self.next_outage == 0.0:
                self.next_outage = now + self.config.outage_interval
            
            # Check Outage Start
            if now >= self.next_outage and now > self.outage_end:
                 self.outage_end = now + self.config.outage_duration
                 self.next_outage = self.outage_end + self.config.outage_interval
                 logger.warning(f"[CHAOS] DATA CENTER OUTAGE STARTED. Ends at {self.outage_end}")

            # Check In Outage
            if now < self.outage_end:
                delay = self.outage_end - now
            else:
                # Normal jitter if enabled
                if self.config.jitter_rate > 0 and self._rng.random() < self.config.jitter_rate:
                    delay = sample_range(low, high)

        # Legacy Jitter (Default)
        elif self.config.jitter_rate > 0 and high > 0:
            if self._rng.random() < self.config.jitter_rate:
                delay = sample_range(low, high)
        
        return delay


    async def intercept_action(self, agent_id: str, action: str) -> bool:
        """
        Intercepts an agent active action.
        Returns False if action should be dropped/failed.
        """
        if not self.config.enabled:
            return True
            
        # 1. Action Dropping
        if self.config.drop_rate > 0:
            if self._rng.random() < self.config.drop_rate:
                logger.warning(f"[CHAOS] Dropping action '{action}' from {agent_id}")
                return False
                
        # 2. Network Partition
        if self.config.network_partition:
             logger.warning(f"[CHAOS] Network Partition blocked {agent_id}")
             # Simulate severe delay or just fail? 
             # Usually partition means "I can't talk to anybody"
             # Let's say it drops for now
             return False

        # 3. Latency
        delay = self._calculate_delay()
        
        if delay > 0:
             if delay == float('inf'):
                 # Special case for "infinite" latency (timeout simulation)
                 # In a real system, this would be await asyncio.Future() or similar
                 # For the fuzzer, we just sleep for a long time or log.
                 logger.error(f"[CHAOS] {agent_id} hit INFINITE latency - hanging.")
                 await asyncio.sleep(3600) # 1 hour
             else:
                 await asyncio.sleep(delay)
             
        return True

    def update_config(self, new_config: Dict[str, Any]):
        """Runtime update of chaos params"""
        for k, v in new_config.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        # Re-run post init to validate
        self.config.__post_init__()
        logger.info(f"Adversarial Config Updated: {self.config}")

