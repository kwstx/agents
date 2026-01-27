import unittest
import sys
import os

# Path Setup
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

from agent_forge.core.compliance import ComplianceAuditor, Violation

class TestCompliance(unittest.TestCase):
    
    def setUp(self):
        self.auditor = ComplianceAuditor(grid_size=10)

    def test_valid_state(self):
        """Verify normal state raises no violations."""
        print("\n--- Test Valid State ---")
        state = {"position": (5, 5), "battery": 100.0}
        violations = self.auditor.audit_state("agent_valid", state)
        print(f"Violations: {violations}")
        self.assertEqual(len(violations), 0)

    def test_battery_violation(self):
        """Verify negative battery is detected."""
        print("\n--- Test Battery Violation ---")
        state = {"position": (5, 5), "battery": -0.1}
        violations = self.auditor.audit_state("agent_bad_batt", state)
        
        print(f"Violations: {violations}")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "PHYSICS_BATTERY_NEGATIVE")
        self.assertIn("negative", violations[0].message)

    def test_boundary_violation(self):
        """Verify out-of-bounds position is detected."""
        print("\n--- Test Boundary Violation ---")
        # Grid size is 10 (0-9). 10 is violation.
        state = {"position": (10, 5), "battery": 50.0}
        violations = self.auditor.audit_state("agent_oob", state)
        
        print(f"Violations: {violations}")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "BOUNDARY_OUT_OF_BOUNDS")
        
        # Test Negative check
        state_neg = {"position": (-1, 5), "battery": 50.0}
        violations_neg = self.auditor.audit_state("agent_oob_neg", state_neg)
        self.assertEqual(len(violations_neg), 1)

    def test_edge_case_zero_battery(self):
        """Verify battery=0 is ALLOWED (Dead Agent)."""
        print("\n--- Test Edge Case: Zero Battery ---")
        state = {"position": (5, 5), "battery": 0.0}
        violations = self.auditor.audit_state("agent_dead", state)
        
        print(f"Violations: {violations}")
        self.assertEqual(len(violations), 0, "Zero battery should be valid (dead)")

if __name__ == "__main__":
    unittest.main()
