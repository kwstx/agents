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
    
    # Profile Configs
    profile_name: str = "custom"      # custom, flaky_wifi, data_center_outage
    spike_chance: float = 0.05        # Prob of entering spike mode (flaky_wifi)
    spike_multiplier: float = 10.0    # Latency multiplier during spike (flaky_wifi)
    outage_interval: float = 30.0     # Seconds between outages
    outage_duration: float = 5.0      # Duration of outage
    
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
                
        # 2. Latency Profiles
        delay = 0.0
        
        # Profile: Flaky Wi-Fi (Bursty Spikes)
        if self.config.profile_name == "flaky_wifi":
            # Simple Markov Model for Burstiness
            # State: self.in_burst (persisted in middleware instance)
            if not hasattr(self, "in_burst"): self.in_burst = False
            
            # Transition Probabilities
            # P(Enter Burst | Normal) = config.spike_chance
            # P(Exit Burst | Burst) = 0.3 (hardcoded for "cluster" feel, or configurable)
            
            check = random.random()
            if self.in_burst:
                if check < 0.3: # 30% chance to recover
                    self.in_burst = False
            else:
                if check < self.config.spike_chance:
                    self.in_burst = True
                    
            if self.in_burst:
                # Spike!
                base = random.uniform(*self.config.latency_range)
                delay = base * self.config.spike_multiplier
            else:
                # Normal Low Latency
                delay = random.uniform(*self.config.latency_range)

        # Profile: Data Center Outage (Sustained Blocking)
        elif self.config.profile_name == "data_center_outage":
            import time
            now = time.time()
            
            # Init state
            if not hasattr(self, "outage_end"): self.outage_end = 0.0
            if not hasattr(self, "next_outage"): 
                self.next_outage = now + self.config.outage_interval
            
            # Check Outage Start
            if now >= self.next_outage and now > self.outage_end:
                 self.outage_end = now + self.config.outage_duration
                 self.next_outage = self.outage_end + self.config.outage_interval
                 logger.warning(f"[CHAOS] DATA CENTER OUTAGE STARTED. Ends at {self.outage_end}")

            # Check In Outage
            if now < self.outage_end:
                # Blocking: Sleep for remaining duration
                remaining = self.outage_end - now
                if remaining > 0:
                    # logger.warning(f"[CHAOS] Agent {agent_id} blocked by outage for {remaining:.2f}s")
                    delay = remaining
            else:
                # Normal jitter if enabled
                if self.config.jitter_rate > 0 and random.random() < self.config.jitter_rate:
                    delay = random.uniform(*self.config.latency_range)

        # Legacy Jitter (Default)
        elif self.config.jitter_rate > 0 and self.config.latency_range[1] > 0:
            if random.random() < self.config.jitter_rate:
                delay = random.uniform(*self.config.latency_range)
        
        if delay > 0:
             await asyncio.sleep(delay)
             
        return True

    def update_config(self, new_config: Dict[str, Any]):
        """Runtime update of chaos params"""
        for k, v in new_config.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        logger.info(f"Adversarial Config Updated: {self.config}")
