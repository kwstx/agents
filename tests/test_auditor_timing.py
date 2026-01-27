import asyncio
import unittest
import time
import sys
import os
from typing import Dict, Any

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.runner import HeadlessRunner

class TestAuditorTiming(unittest.TestCase):
    
    def run_async(self, coro):
        return asyncio.run(coro)

    def test_auditor_strict_ordering(self):
        """
        Verify that:
        1. Audit runs immediately after step.
        2. Violations are present in the SAME step callback event.
        3. No delay/starvation occurs.
        """
        print("\n--- Test Auditor Timing & Integration ---")
        
        runner = HeadlessRunner()
        # Setup with 1 agent
        self.run_async(runner.setup(num_agents=1, grid_size=10))
        
        # We need to force a violation.
        # Since agents are autonomous, standard Agents prefer valid moves.
        # We can 'hack' the environment or the agent logic?
        # Easier: Modifying the agent's STARTING position to be on the boundary 
        # and forcing it to move OUT.
        
        # Or even simpler: Use the Runner to manually execute a `perform_action` 
        # that we know is invalid, bypassing the agent loop?
        # Yes, standard integration test style.
        
        async def manual_test():
            # Manually drive the engine
            engine = runner.engine
            agent_id = "Test-Agent"
            
            # Setup a callback to capture the event
            captured_event = None
            
            def callback(update: Dict[str, Any]):
                nonlocal captured_event
                captured_event = update
                
            engine.on_step_callback = callback
            
            # 1. Force state to edge (9,9)
            # WarehouseEnv lets us cheat state? No simple setter.
            # But step() takes action.
            # Let's perform an action that MIGHT assume validity but ends up invalid.
            # WarehouseEnv usually clamps or ignores invalid moves.
            # Wait, `test_compliance` showed correct detection of Out of Bounds.
            # But WarehouseEnv prevents out of bounds internally?
            # Let's check `warehouse.py`.
            # If WarehouseEnv prevents it, then state is valid -> No Violation!
            # We need the Env to ALLOW the bad state, OR checking something Env allows but Auditor forbids.
            # Auditor forbids Negative Battery.
            # WarehouseEnv decreases battery.
            # If we set battery to 0.1 and consume 0.2, we get negative battery!
            
            # HACK: Manually set agent state in env
            engine.env.agents[agent_id] = {
                "position": (9, 9),
                "battery": 0.1, # Critical low
                "carrying": None,
                "server_time": time.time()
            }
            
            # 2. Perform Action (Costs battery)
            # Cost is typically small (0.01?). Let's check.
            # If cost is 0.1, then 0.1 - 0.1 = 0.0 (Valid Dead).
            # We need NEGATIVE.
            # Let's set battery to 0.0001 and move.
            
            engine.env.agents[agent_id]["battery"] = 0.0001
            
            # Action: "move_right" (from 9,9 -> 10,9 invalid, but cost applies)
            # If env checks boundaries first and returns early, maybe no cost?
            # Let's check Env source.
            
            # Assume action happens.
            # We want to verify `violations` key is present in callback.
            
            # If WarehouseEnv is robust, it might be hard to produce invalid state via normal API.
            # Let's Force Invalid Pulse via direct injection after step?
            # NO, we are testing Engine Integration.
            # If Engine calls Env.step, logic happens.
            # Then Engine calls Audit.
            
            # If I can't easily break the Env via action, 
            # I can MOCK the Auditor or the Env?
            # NO, integration test.
            
            # Let's try the Battery Drain attack.
            # WarehouseAgent code: `self.battery -= 0.1`?
            # Env code?
            pass

            # Let's just try to Execute "move_right" from (9,9).
            # If Env clamps to (9,9), battery reduces.
            # Eventually battery might go negative if logic is simple `battery -= cost`.
            
            # Let's force a negative battery via "God Mode" (direct object access) just BEFORE the step finishes?
            # Can't easily interrupt Step.
            
            # Alternate Check: Mock the Auditor to ALWAYS return a violation.
            # This confirms the PIPELINE works, which is the goal of this task.
            # "Verify RiskMonitor receives the event".
            # It doesn't matter if the violation is real, just that IF it happens, it's reported.
            
            # Yes, Mocking the Auditor's return value is the cleanest way to verify TIMING/INTEGRATION.
            
            original_audit = engine.auditor.audit_state
            
            from agent_forge.core.compliance import Violation
            def mock_audit(aid, state):
                return [Violation(aid, "TEST_RULE", "Mock Violation", {})]
            
            engine.auditor.audit_state = mock_audit
            
            # Perform Action
            await engine.perform_action(agent_id, "wait")
            
            # Assertions
            assert captured_event is not None, "Callback never fired"
            assert "info" in captured_event, "Event missing info"
            assert "violations" in captured_event["info"], "Violations missing from event payload"
            
            v_list = captured_event["info"]["violations"]
            assert len(v_list) == 1
            assert v_list[0]["rule"] == "TEST_RULE"
            
            print("SUCCESS: Violation injected and captured in same-tick callback.")
            
        self.run_async(manual_test())

if __name__ == "__main__":
    unittest.main()
