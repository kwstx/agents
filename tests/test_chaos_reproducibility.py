import unittest
import asyncio
import time
import sys
import os
import random
from typing import Dict, Any, List

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.core.compliance import Violation

class TestChaosReproducibility(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)
    
    def run_chaos_scenario(self, seed: int) -> List[float]:
        """
        Runs a standard chaos scenario with a specific seed.
        We MOCK time to ensure deterministic physics.
        """
        # Config: High Jitter, High Drain (Volatile)
        env_config = {
            "battery_drain_rate": 5.0,
            "safety_rails": False
        }
        env = WarehouseEnv(size=10, config=env_config)
        
        stress_config = {
            "seed": seed,
            "latency_rate": 0.5,           # 50% chance
            "latency_range": (0.01, 0.1)   # Variable delay
        }
        
        engine = SimulationEngine(env, stress_config=stress_config)
        agent_id = "test_agent"
        
        # --- MOCK TIME ARCHITECTURE ---
        # We need to capture the env's time calls AND the middleware's sleep calls.
        
        current_sim_time = 1000.0 # Start at arbitrary time
        
        # Patch Env's time usage? 
        # WarehouseEnv calls `time.time()`.
        # Engine calls `time.time()` for timestamps.
        # Adversary calls `asyncio.sleep`.
        
        # We will use a context manager to patch time module? 
        # Easier: Just replace the methods on the instances if possible or use unittest.mock.
        # But `time.time` is built-in.
        
        # Let's use customized Env injection or just mock `time.time` globally for the duration of loop.
        
        # Init Env with mocked time
        env.agents[agent_id] = {
            "position": (1, 1),
            "battery": 100.0,
            "carrying": None,
            "server_time": current_sim_time
        }
        
        fingerprint = []
        
        # Save original
        original_sleep = asyncio.sleep
        original_time = time.time
        
        # Mock Sleep: Advance time by requested amount instantly
        async def mock_sleep(delay):
            nonlocal current_sim_time
            current_sim_time += delay
            return
            
        # Mock Time: Return current simulated time
        def mock_time():
            return current_sim_time
            
        # Apply Mocks
        asyncio.sleep = mock_sleep
        time.time = mock_time
        
        # We also need to patch random because we reset it in the loop??
        # No, Engine seeding handles random state.
        
        try:
            async def loop():
                for i in range(10):
                    # Action: Random Move
                    actions = ["UP", "DOWN", "LEFT", "RIGHT"]
                    action = random.choice(actions) 
                    
                    # We might need to advance time slightly for "computation overhead" 
                    # to prevent 0-delta if no sleep happens?
                    nonlocal current_sim_time
                    current_sim_time += 0.001 
                    
                    await engine.perform_action(agent_id, action)
                    
                    # Capture State
                    # State physics relies on `server_time` delta.
                    # Since we patched time.time, `WarehouseEnv.step` will use `mock_time`.
                    # Adversary `intercept_action` calls `asyncio.sleep` -> `mock_sleep` -> advances time.
                    # Therefore, battery drain should be deterministic calculation of (random_delay + 0.001) * rate.
                    
                    state = await engine.get_state(agent_id)
                    fingerprint.append(state["battery"])
                    
                    # Also capture position to verify random action choice determinism
                    fingerprint.append(state["position"][0]) 
                    
            self.run_async(loop())
            
        finally:
            # Restore
            asyncio.sleep = original_sleep
            time.time = original_time
            
        return fingerprint

    def test_reproducibility(self):
        """
        Run twice with Seed 42. Verify identical traces.
        Run once with Seed 999. Verify different trace.
        """
        print("\n--- Chaos Reproducibility ---")
        
        print("Run 1 (Seed 42)...")
        trace_1 = self.run_chaos_scenario(42)
        print(f"Trace 1: {trace_1}")
        
        print("Run 2 (Seed 42)...")
        trace_2 = self.run_chaos_scenario(42)
        print(f"Trace 2: {trace_2}")
        
        print("Run 3 (Seed 999)...")
        trace_3 = self.run_chaos_scenario(999)
        print(f"Trace 3: {trace_3}")
        
        # Verification
        self.assertEqual(trace_1, trace_2, "Chaos runs with same seed produced different results!")
        self.assertNotEqual(trace_1, trace_3, "Different seeds produced identical results (Unlikely unless deterministic logic is broken)")
        
        print("SUCCESS: Chaos is deterministic via seeding.")

if __name__ == "__main__":
    unittest.main()
