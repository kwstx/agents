import asyncio
import time
import random
import sys
import os
import unittest
import numpy as np
from dataclasses import dataclass

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.adversarial import AdversarialMiddleware, AdversarialConfig

class TestLatencyInjector(unittest.TestCase):
    
    def setUp(self):
        # Ensure clean state
        pass

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_zero_jitter(self):
        """Verify jitter_rate=0.0 produces NO delays."""
        print("\n--- Test Zero Jitter (0.0) ---")
        config = AdversarialConfig(
            enabled=True,
            jitter_rate=0.0,
            latency_range=(0.01, 0.05) # Even if range exists, rate 0 should disable it
        )
        middleware = AdversarialMiddleware(config)
        
        delays = []
        iterations = 1000
        
        async def run_loop():
            for _ in range(iterations):
                start = time.perf_counter()
                await middleware.intercept_action("test_agent", "move")
                duration = time.perf_counter() - start
                delays.append(duration)
                
        self.run_async(run_loop())
        
        # In pure async with 0 sleep, overhead should be negligible (<1ms usually)
        # We check if any significant delay occurred
        max_delay = max(delays)
        print(f"Max Delay encountered: {max_delay*1000:.3f}ms")
        
        # Threshold: 5ms (generous for overhead, but well below 10ms range min)
        self.assertLess(max_delay, 0.005, "Zero jitter should not introduce significant latency")

    def test_full_jitter(self):
        """Verify jitter_rate=1.0 applied delays every time."""
        print("\n--- Test Full Jitter (1.0) ---")
        min_lat, max_lat = 0.01, 0.02 # 10ms - 20ms
        config = AdversarialConfig(
            enabled=True,
            jitter_rate=1.0,
            latency_range=(min_lat, max_lat)
        )
        middleware = AdversarialMiddleware(config)
        
        delays = []
        iterations = 100
        
        async def run_loop():
            for _ in range(iterations):
                start = time.perf_counter()
                await middleware.intercept_action("test_agent", "move")
                duration = time.perf_counter() - start
                delays.append(duration)
        
        self.run_async(run_loop())
        
        # Verify all are within range (plus/minus small overhead)
        # We allow small margin for python scheduler overhead
        margin_lower = 0.0001 # It typically sleeps at least requested
        margin_upper = 0.01   # Windows scheduler can be jumpy
        
        min_observed = min(delays)
        max_observed = max(delays)
        print(f"Latency Range Config: {min_lat*1000:.1f}ms - {max_lat*1000:.1f}ms")
        print(f"Observed Range: {min_observed*1000:.2f}ms - {max_observed*1000:.2f}ms")
        
        self.assertGreaterEqual(min_observed, min_lat - 0.005, "Latency too low (execution faster than sleep?)")
        # We don't strictly assert max because OS scheduler can pause process, 
        # but we check reasonable bounds for unit test
        
        # Check that we actually slept roughly the right amount
        avg = np.mean(delays)
        self.assertGreater(avg, min_lat, "Average latency should be above min")


    def test_partial_jitter_statistics(self):
        """Verify jitter_rate=0.5 produces ~50% hits."""
        print("\n--- Test Partial Jitter (0.5) ---")
        target_rate = 0.5
        iterations = 2000
        min_lat = 0.01 # 10ms
        
        config = AdversarialConfig(
            enabled=True,
            jitter_rate=target_rate,
            latency_range=(min_lat, min_lat) # Fixed latency for easy detection
        )
        middleware = AdversarialMiddleware(config)
        
        hits = 0
        
        async def run_loop():
            nonlocal hits
            for _ in range(iterations):
                start = time.perf_counter()
                await middleware.intercept_action("test_agent", "move")
                duration = time.perf_counter() - start
                
                # If duration > 0.5 * min_lat, we count it as a hit
                # (Overhead is usually << 10ms)
                if duration >= min_lat * 0.8:
                    hits += 1
                    
        self.run_async(run_loop())
        
        observed_rate = hits / iterations
        print(f"Target Rate: {target_rate}")
        print(f"Observed Rate: {observed_rate} ({hits}/{iterations})")
        
        # Standard Error for proportion: sqrt(p(1-p)/n)
        # 0.5 * 0.5 / 2000 = 0.000125. sqrt ~= 0.011
        # 3 sigma ~= 0.033
        margin = 0.05 
        
        self.assertAlmostEqual(observed_rate, target_rate, delta=margin, 
                             msg=f" observed rate {observed_rate} deviates from {target_rate}")

    def test_distribution_uniform(self):
        """Verify latency follows Uniform distribution."""
        print("\n--- Test Distribution Uniform ---")
        min_lat, max_lat = 0.01, 0.03 # 10ms - 30ms
        iterations = 5000 # Need more samples for distribution check
        
        config = AdversarialConfig(
            enabled=True,
            jitter_rate=1.0, # Always apply
            latency_range=(min_lat, max_lat)
        )
        middleware = AdversarialMiddleware(config)
        
        delays = []
        
        async def run_loop():
            # To speed up test, strict 5000 sleeps of 10ms = 50s. Too slow.
            # We mock asyncio.sleep to just record the value requested!
            # This isolates the logic from the OS scheduler.
            
            nonlocal delays
            original_sleep = asyncio.sleep
            
            async def mock_sleep(delay):
                delays.append(delay)
                # Don't actually sleep
                return
                
            asyncio.sleep = mock_sleep
            try:
                for _ in range(iterations):
                    await middleware.intercept_action("test_agent", "move")
            finally:
                asyncio.sleep = original_sleep
                
        self.run_async(run_loop())
        
        observed_mean = np.mean(delays)
        expected_mean = (min_lat + max_lat) / 2
        
        observed_var = np.var(delays)
        expected_var = ((max_lat - min_lat) ** 2) / 12
        
        print(f"Expected Mean: {expected_mean:.5f}, Observed Mean: {observed_mean:.5f}")
        print(f"Expected Var:  {expected_var:.7f}, Observed Var:  {observed_var:.7f}")
        
        self.assertAlmostEqual(observed_mean, expected_mean, delta=0.001)
        self.assertAlmostEqual(observed_var, expected_var, delta=0.0001)
        
        # Verify Min/Max bounds strictly
        self.assertTrue(all(d >= min_lat for d in delays))
        self.assertTrue(all(d <= max_lat for d in delays))


if __name__ == "__main__":
    unittest.main()
