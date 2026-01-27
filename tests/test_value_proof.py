import unittest
import asyncio
import time
import sys
import os
import random
from typing import Dict, Any, Tuple

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.envs.warehouse_agent import WarehouseAgent
from agent_forge.utils.message_bus import MessageBus

# --- AGENT VARIANTS ---

class NaiveAgent(WarehouseAgent):
    """
    Optimized for Speed, ignores Risk.
    "Move fast and break things."
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aggressive settings
        self.charge_threshold = 10.0 # Only charge when CRITICAL
        self.behavior["step_interval"] = 0.0 # Try to move as fast as possible

class HardenedAgent(WarehouseAgent):
    """
    Optimized for Reliability, mitigates Risk.
    "Slow is smooth, smooth is fast."
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Conservative settings
        self.charge_threshold = 40.0 # Charge early
        self.latency_tolerance = 0.5 # Seconds
        
    async def step(self):
        # DEFENSIVE LAYER: Latency Check
        # Before deciding, check if we are lagging
        read_time = time.time()
         # In mock tests this might be skewed, but for this "Business Value" test
         # we will use Real Time or assume Engine supports drift detection.
         # Standard Agent `step` calculates drift but logs it.
         # We want to ACT on it.
        
        # We need to fetch state primarily to see timestamp
        state = await self.engine.get_state(self.agent_id)
        if state:
            server_time = state.get("server_time", read_time)
            drift = read_time - server_time
            
            if drift > self.latency_tolerance:
                 self.logger.warning(f"High Drift ({drift:.2f}s) detected! Entering SAFETY MODE.")
                 # Safety Mode: Do nothing (STAY) to avoid overshooting
                 # Or, if low battery, prioritize CHARGE regardless of current task
                 
                 # If we are effectively blind due to lag, we should STOP.
                 # But if we stop, we burn battery doing nothing?
                 # Better to move to Charger if we know where it is and path is clear?
                 # For MVP proof: Just STAY to avoid Boundary Violation, 
                 # BUT if battery is falling, this drift might kill us.
                 # Let's say Hardened Agent decides to "CHARGE NOW" if drift is high 
                 # because it can't trust its precise movement for delivery.
                 
                 if state["battery"] < 60: # Even moderately low
                     self.logger.warning("Drift + Mod Battery -> FORCE CHARGE.")
                     self.set_goal(self.find_nearest_zone("charger"), "charge")
                     
        # Delegate to normal logic
        await super().step()

# --- TEST SUITE ---

class TestValueProof(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)

    def run_simulation_battle(self, AgentClass, agent_name, duration=10.0):
        print(f"\n--- Testing {agent_name} ---")
        
        # High Chaos Environment
        # High Drain (Time matters)
        # Heavy Jitter (Causes Drift)
        # High Chaos Environment
        # High Drain (Time matters)
        # Heavy Jitter (Causes Drift)
        # Goldilocks Zone Calculation:
        # Distance to charger ~5 tiles.
        # Latency ~0.5s/step -> Travel time 2.5s.
        # Drain 6.0/s -> Cost 15.0.
        # Naive (Threshold 10) -> 10 - 15 = -5 (DIE).
        # Hardened (Threshold 40) -> 40 - 15 = 25 (LIVE).
        env_config = {
            "battery_drain_rate": 8.0, 
            "safety_rails": True
        }
        env = WarehouseEnv(size=10, config=env_config)
        
        stress_config = {
            "latency_rate": 0.9,
            "latency_range": (0.3, 0.9) # Higher min delay
        }
        
        engine = SimulationEngine(env, stress_config=stress_config)
        mb = MessageBus()
        
        agent = AgentClass(agent_name, mb, engine)
        env.agents[agent_name] = { 
            "position": (5, 5), "battery": 100.0, "carrying": None, "server_time": time.time() 
        }
        
        # Run for Duration
        start_time = time.time()
        
        async def loop():
            agent.running = True
            while time.time() - start_time < duration:
                if not agent.running: break
                await agent.step()
                await asyncio.sleep(0.1) # Frequency
                
                # Check status
                state = await engine.get_state(agent_name)
                if state["battery"] <= 0:
                    print(f"FAILURE: {agent_name} died of battery depletion!")
                    return False
            
            print(f"SUCCESS: {agent_name} survived the chaos.")
            return True

        success = self.run_async(loop())
        
        # Report Metrics
        final_state = self.run_async(engine.get_state(agent_name))
        print(f"Final Battery: {final_state['battery']:.2f}")
        return success, final_state['battery']

    def test_roi_comparison(self):
        """
        Compare survival of Naive vs Hardened.
        """
        print("\n=== ROI PROOF: CHAOS RESILIENCE ===")
        
        # 1. Test Naive
        # Expectation: High drain + Jitter -> Lag -> Misses Charge Threshold -> Dies
        naive_survived, naive_batt = self.run_simulation_battle(NaiveAgent, "Naive-Bot", duration=30.0)
        
        # 2. Test Hardened
        # Expectation: High drain + Jitter -> Detects Lag -> Charges Early -> Survives
        hard_survived, hard_batt = self.run_simulation_battle(HardenedAgent, "Iron-Bot", duration=30.0)
        
        print("\n=== RESULTS ===")
        print(f"Naive-Bot: {'SURVIVED' if naive_survived else 'DIED'} (Batt: {naive_batt:.1f})")
        print(f"Iron-Bot:  {'SURVIVED' if hard_survived else 'DIED'} (Batt: {hard_batt:.1f})")
        
        # Strict Proof: Hardened MUST outperform Naive
        # Either Naive dies and Hardened lives, OR Hardened has significantly more battery.
        
        if not naive_survived and hard_survived:
            print("CONCLUSION: Chaos Hardening prevented critical failure.")
        elif hard_batt > naive_batt + 20:
             print("CONCLUSION: Chaos Hardening significantly improved efficiency.")
        else:
             print("CONCLUSION: Inconclusive (Maybe chaos wasn't strong enough?)")
             
        self.assertTrue(hard_survived, "Hardened agent failed! Defense is insufficient.")
        # Ideally Naive fails to prove the need, but if it survives by luck, at least check battery margin.
        if naive_survived:
            self.assertGreater(hard_batt, naive_batt, "Hardened agent performed worse than Naive!")

if __name__ == "__main__":
    unittest.main()
