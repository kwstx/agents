import unittest
import asyncio
import time
import sys
import os
from typing import Dict, Any

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.core.risk import RiskMonitor, RiskLevel
from agent_forge.core.compliance import Violation

class TestChaosCompliance(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)
        
    def setUp(self):
        # Configure env to be dangerous
        self.env_config = {
            "battery_drain_rate": 5.0, # High drain per second
            "safety_rails": False      # Allow out of bounds
        }
        self.env = WarehouseEnv(size=5, config=self.env_config)
        self.risk_monitor = RiskMonitor()
        
    def test_latency_induces_battery_failure(self):
        """
        Scenario: Latency causes processing time to exceed battery reserves.
        """
        print("\n--- Chaos Scenario 1: Latency -> Battery Death ---")
        
        # 1. Setup Engine with Latency
        stress_config = {
            "latency_rate": 1.0,         # Always apply
            "latency_range": (0.2, 0.4)  # 200ms - 400ms delay per step
        }
        engine = SimulationEngine(self.env, stress_config=stress_config)
        # Fix Auditor Grid Size to match Env
        engine.auditor.grid_size = self.env.size
        
        # 2. Setup Agent with Low Battery
        agent_id = "victim_agent"
        # Manually inject state
        self.env.agents[agent_id] = {
            "position": (2, 2),
            "battery": 1.0, # Very low. 1.0 battery. 
                            # Drain rate 5.0/s. 
                            # Dies in 0.2s.
            "carrying": None,
            "server_time": time.time()
        }
        
        # 3. Monitor for Violations
        caught_violations = []
        
        async def callback(update):
            if "info" in update and "violations" in update["info"]:
                # Convert dicts back to Violation objects relative to RiskMonitor needs?
                # RiskMonitor expects text/dict from JSON
                self.risk_monitor.record_violations(update["agent_id"], update["info"]["violations"])
                caught_violations.extend(update["info"]["violations"])
                
        engine.on_step_callback = callback
        
        # 4. Execute Action
        # Agent tries to move. Latency is 0.2s minimum.
        # Battery drain = 0.2 * 5.0 = 1.0. 
        # Battery goes from 1.0 -> 0.0 (Dead) or slightly negative depending on exact timing.
        
        print("Executing step with latency...")
        self.run_async(engine.perform_action(agent_id, "UP"))
        
        # Check Agent State
        state = self.run_async(engine.get_state(agent_id))
        print(f"Final Battery: {state['battery']}")
        
        # Check Compliance
        # Battery < 0 triggers PHYSICS_BATTERY_NEGATIVE
        # If it's exactly 0, maybe not violation? (Compliance says < 0)
        # With 0.2 to 0.4s delay, likely > 1.0 cost. So < -0.X battery.
        
        has_battery_violation = any("BATTERY" in v["rule"] for v in caught_violations)
        
        if not has_battery_violation:
             print("WARNING: Battery did not go negative? Maybe latency was too low.")
             # assert state['battery'] < 0
        
        self.assertTrue(has_battery_violation, "Compliance Auditor should catch negative battery caused by latency")
        
        # Check Risk Monitor
        risk = self.risk_monitor.get_risk_level(agent_id)
        print(f"Risk Level: {risk}")
        # Battery violation is weighted 40. 
        # Initial score 0 -> 40 (MEDIUM).
        self.assertIn(risk, [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL])

    def test_delayed_action_boundary_violation(self):
        """
        Scenario: Delayed actions cause safety limits to be exceeded (Drift/Overshoot).
        We simulate an agent sending multiple move commands that pile up.
        """
        print("\n--- Chaos Scenario 2: Stale Decisions -> Boundary Violation ---")
        
        # 1. Setup Engine with High Latency
        stress_config = {
            "latency_rate": 1.0,
            "latency_range": (0.1, 0.1) 
        }
        engine = SimulationEngine(self.env, stress_config=stress_config)
        engine.auditor.grid_size = self.env.size
        agent_id = "drift_agent"
        
        # Start near edge (size=5, max index 4). Start at 4.
        self.env.agents[agent_id] = {
            "position": (4, 2),
            "battery": 100.0,
            "carrying": None,
            "server_time": time.time()
        }
        
        # Hook up RiskMonitor
        async def callback(update):
            if "info" in update and "violations" in update["info"]:
                self.risk_monitor.record_violations(update["agent_id"], update["info"]["violations"])
                
        engine.on_step_callback = callback
        
        # 2. Execute Action: Move RIGHT (into void)
        # Check Risk BEFORE
        print(f"Initial Risk: {self.risk_monitor.get_risk_level(agent_id)}")
        
        # Run step
        self.run_async(engine.perform_action(agent_id, "RIGHT"))
        
        # 3. Verify Violation
        state = self.run_async(engine.get_state(agent_id))
        print(f"Position: {state['position']}")
        
        # Should be (5, 2) which is OOB
        
        # Check Risk AFTER
        final_risk = self.risk_monitor.get_risk_level(agent_id)
        print(f"Final Risk: {final_risk}")
        
        # We expect MEDIUM/HIGH risk due to Boundary Violation (30 pts)
        self.assertIn(final_risk, [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL])
        
        # Verify causal chain in Logs (History)
        history = self.risk_monitor.history
        self.assertTrue(len(history) > 0)
        print(f"Violation History: {history}")
        self.assertIn("BOUNDARY", history[0]["violation"]["rule"])

    def test_recovery_failure_under_jitter(self):
        """
        Scenario: Recovery logic fails under repeated jitter.
        We simulate a sequence where agent tries to correct but fails due to jitter.
        Basically verify that multiple violations accumulate risk to CRITICAL.
        """
        print("\n--- Chaos Scenario 3: Accumulated Risk (Recovery Failure) ---")
        
        engine = SimulationEngine(self.env) # No stress needed for this logic check
        engine.auditor.grid_size = self.env.size
        agent_id = "risk_agent"
        
        # Hook callback
        def callback(update):
             if "info" in update and "violations" in update["info"]:
                self.risk_monitor.record_violations(update["agent_id"], update["info"]["violations"])
        engine.on_step_callback = callback
        
        self.env.agents[agent_id] = { "position": (4, 2), "battery": 100, "server_time": time.time() }
        
        # Repeatedly bang against the wall (simulating failed recovery)
        async def run_scenario():
            for _ in range(3):
                await engine.perform_action(agent_id, "RIGHT") # Violation!
                
        self.run_async(run_scenario())
        
        risk = self.risk_monitor.get_risk_level(agent_id)
        
        # 3 violations * 30 = 90. That is HIGH (>60).
        self.assertTrue(len(self.risk_monitor.history) > 0, "No violations recorded in history")
        self.assertNotEqual(risk, RiskLevel.LOW, "Risk should increase above LOW")
        
        # Do one more
        self.run_async(engine.perform_action(agent_id, "RIGHT"))
        risk = self.risk_monitor.get_risk_level(agent_id)
        # 120 -> CRITICAL
        self.assertEqual(risk, RiskLevel.CRITICAL)

if __name__ == "__main__":
    unittest.main()
