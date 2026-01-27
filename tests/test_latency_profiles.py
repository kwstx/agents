import asyncio
import time
import unittest
import numpy as np
import sys
import os

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.adversarial import AdversarialMiddleware, AdversarialConfig

class TestLatencyProfiles(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)

    def test_flaky_wifi_burstiness(self):
        """Verify Flaky Wi-Fi produces bursty spikes."""
        print("\n--- Test Profile: Flaky Wi-Fi ---")
        base_lat = 0.001 # 1ms base
        spike_mult = 50.0 # 50ms spike
        
        config = AdversarialConfig(
            enabled=True,
            profile_name="flaky_wifi",
            latency_range=(base_lat, base_lat),
            spike_chance=0.1, # 10% chance to start burst
            spike_multiplier=spike_mult
        )
        middleware = AdversarialMiddleware(config)
        
        delays = []
        iterations = 1000
        
        async def run_loop():
            # Mock sleep to just record requested delay
            original_sleep = asyncio.sleep
            async def mock_sleep(d):
                delays.append(d)
                return
            asyncio.sleep = mock_sleep
            
            try:
                for _ in range(iterations):
                    await middleware.intercept_action("test", "test")
            finally:
                asyncio.sleep = original_sleep
                
        self.run_async(run_loop())
        
        # Analysis
        high_latency = base_lat * spike_mult
        spikes = [d for d in delays if d >= high_latency * 0.9]
        spike_count = len(spikes)
        spike_rate = spike_count / iterations
        
        print(f"Base Latency: {base_lat}s, Spike: {high_latency}s")
        print(f"Total Spikes: {spike_count}/{iterations} ({spike_rate*100:.1f}%)")
        
        # Verify spikes exist
        self.assertGreater(spike_count, 0, "No spikes generated in flaky wifi mode")
        
        # Verify Clustering (Burstiness)
        # Check if spikes are adjacent more often than random
        adjacent_spikes = 0
        for i in range(len(delays)-1):
            if delays[i] >= high_latency * 0.9 and delays[i+1] >= high_latency * 0.9:
                adjacent_spikes += 1
                
        print(f"Adjacent Spikes: {adjacent_spikes}")
        
        # If random, P(Spike) = spike_rate (roughly). P(Adj) = rate * rate
        # With clustering, P(Adj) should be significantly higher.
        # Our Markov model: P(Burst|Burst) = 0.7 (since exit is 0.3)
        # So we expect ~70% of spikes to be followed by a spike.
        
        expected_adj_if_clustered = spike_count * 0.6 # Strict lower bound
        self.assertGreater(adjacent_spikes, expected_adj_if_clustered, 
                         f"Spikes not clustering enough. Found {adjacent_spikes}, Expected > {expected_adj_if_clustered}")


    def test_data_center_outage(self):
        """Verify Data Center Outage blocks execution periodically."""
        print("\n--- Test Profile: Data Center Outage ---")
        interval = 0.5 # Fast interval for test
        duration = 0.2 # 200ms outage
        
        config = AdversarialConfig(
            enabled=True,
            profile_name="data_center_outage",
            outage_interval=interval,
            outage_duration=duration
        )
        middleware = AdversarialMiddleware(config)
        
        delays = []
        timestamps = []
        
        async def run_loop():
            start_time = time.time()
            
            # Mock sleep to run fast simulation
            # We need to simulate time passing though!
            # So we will manually advance a "simulated clock" if we mock sleep?
            # Or just use real sleep for this specific test since intervals are small.
            # Using real sleep is safer to verify "Blocking" behavior.
            
            for _ in range(20):
                t0 = time.time()
                await middleware.intercept_action("test", "test")
                dt = time.time() - t0
                
                delays.append(dt)
                timestamps.append(time.time() - start_time)
                
                # Small step interval between checks
                await asyncio.sleep(0.05) 
                
        self.run_async(run_loop())
        
        # Analysis
        # We expect some delays to be large (> duration - overhead)
        # And periods of small delays.
        
        long_delays = [d for d in delays if d > 0.05]
        print(f"Long Delays (>50ms): {len(long_delays)}")
        print(f"Values: {[f'{d:.3f}' for d in long_delays]}")
        
        self.assertGreater(len(long_delays), 0, "No outage blocking observed")
        
        # Verify blocking value is close to remaining duration
        # Max delay shouldn't exceed duration significantly
        max_delay = max(delays)
        self.assertLess(max_delay, duration + 0.1, "Blocking exceeded outage duration significantly")

if __name__ == "__main__":
    unittest.main()
