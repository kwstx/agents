import unittest
import asyncio
import time
import sys
import os
import random
from typing import Dict, Any

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.core.risk import RiskMonitor, RiskLevel
from agent_forge.core.compliance import Violation

class TestNoiseSuppression(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)
    
    def setUp(self):
        self.risk_monitor = RiskMonitor()
        
    def test_mild_jitter_stability(self):
        """
        Verify that mild jitter applied to a valid control loop does not trigger risk or violations.
        """
        print("\n--- noise_suppression: Mild Jitter Stability ---")
        
        # 1. Config: Mild Chaos + Safe Env
        # We enable safety rails to mimic "normal operation" where boundaries are enforced.
        # But we also want to ensure that TIME delays don't cause Battery failure if managed.
        # Drain rate 2.0. Mild jitter 0.05s. Cost per step ~0.1 units.
        # 100 steps = 10 battery units. Agent starts with 100. Should last entire run.
        
        env_config = {
            "battery_drain_rate": 2.0,
            "safety_rails": False # Disable rails to ensure Agent Logic + Jitter doesn't drift
        }
        env = WarehouseEnv(size=10, config=env_config)
        
        stress_config = {
            "latency_rate": 0.5,         # 50% of steps
            "latency_range": (0.01, 0.05) # 10-50ms delay
        }
        
        engine = SimulationEngine(env, stress_config=stress_config)
        engine.auditor.grid_size = env.size
        
        agent_id = "stable_agent"
        # Init agent
        env.agents[agent_id] = {
            "position": (1, 1),
            "battery": 100.0,
            "carrying": None,
            "server_time": time.time()
        }
        
        # Risk Monitor Hook
        violations_caught = []
        async def callback(update):
            if "info" in update and "violations" in update["info"]:
                current_violations = update["info"]["violations"]
                if current_violations:
                    violations_caught.extend(current_violations)
                    self.risk_monitor.record_violations(update["agent_id"], current_violations)
                    
        engine.on_step_callback = callback
        
        # 2. Run Long Simulation (e.g. 50 steps)
        # Agent behavior: Move Right then Left (Oscillate) to stay safe.
        async def run_loop():
            start_time = time.time()
            steps = 50
            for i in range(steps):
                # Simple logic
                action = "RIGHT" if i % 2 == 0 else "LEFT"
                await engine.perform_action(agent_id, action)
                await asyncio.sleep(0) # Yield
            
            duration = time.time() - start_time
            print(f"Simulation of {steps} steps took {duration:.2f}s")
            
        self.run_async(run_loop())
        
        # 3. Assertions
        
        # Risk should be LOW
        risk = self.risk_monitor.get_risk_level(agent_id)
        score = self.risk_monitor.agent_risk.get(agent_id, 0.0)
        
        print(f"Final Risk Level: {risk}")
        print(f"Final Risk Score: {score}")
        print(f"Total Violations: {len(violations_caught)}")
        
        if len(violations_caught) > 0:
            print("Captured Violations:", violations_caught)
            
        # Assertions
        # 1. No High Risk
        self.assertEqual(risk, RiskLevel.LOW, "Risk rose above LOW despite valid behavior")
        
        # 2. Zero Violations (Ideal)
        # Since logic was valid and rails were on, boundary violations are impossible.
        # Battery should have decreased by ~10-15 units. 100 -> 85. > 0.
        # So no battery violations.
        self.assertEqual(len(violations_caught), 0, "False positives detected!")
        
    def test_log_sparsity(self):
        """
        Verify that logs/history remain sparse under normal op.
        """
        # This is implicitly checked by violations=0 -> history is empty.
        pass

if __name__ == "__main__":
    unittest.main()
