import pytest
import torch
import torch.nn.functional as F
import numpy as np
from models.decision_model import GridDecisionModel

class TestModelRobustness:
    def _calculate_entropy(self, logits):
        probs = F.softmax(logits, dim=1)
        log_probs = torch.log(probs + 1e-9) # Avoid log(0)
        entropy = -torch.sum(probs * log_probs, dim=1)
        return entropy.mean().item()

    def test_noisy_inputs(self):
        """Verify model stability under noisy inputs."""
        model = GridDecisionModel()
        model.eval()
        
        # Valid input
        clean_input = torch.tensor([[0.5, 0.5, 0.8, 0.8]])
        
        # Add noise levels
        noise_levels = [0.1, 0.5, 2.0]
        
        print("\n--- Noise Stress Test ---")
        for sigma in noise_levels:
            noise = torch.randn_like(clean_input) * sigma
            noisy_input = clean_input + noise
            
            output = model(noisy_input)
            entropy = self._calculate_entropy(output)
            
            print(f"Noise Sigma={sigma}: Max Logit={output.max().item():.2f}, Entropy={entropy:.4f}")
            
            assert not torch.isnan(output).any(), f"Output became NaN with noise sigma={sigma}"
            assert not torch.isinf(output).any(), f"Output became Inf with noise sigma={sigma}"

    def test_adversarial_inputs(self):
        """Verify model stability under adversarial / out-of-range inputs."""
        model = GridDecisionModel()
        model.eval()
        
        # Scenarios: Extremely large, Negative (invalid for position but possible as tensor)
        scenarios = {
            "Large Values": torch.tensor([[100.0, 100.0, 100.0, 100.0]]),
            "Negative Values": torch.tensor([[-5.0, -5.0, -5.0, -5.0]]),
            "Mixed Extreme": torch.tensor([[1e5, -1e5, 0.0, 1.0]])
        }
        
        print("\n--- Adversarial Stress Test ---")
        for name, tensor in scenarios.items():
            output = model(tensor)
            entropy = self._calculate_entropy(output)
            
            print(f"Scenario '{name}': Max Logit={output.max().item():.2f}, Entropy={entropy:.4f}")
            
            assert not torch.isnan(output).any(), f"Output became NaN for {name}"
            assert not torch.isinf(output).any(), f"Output became Inf for {name}"
            
            # Note: We rely on the previously added strict structure test to catch NaNs in INPUT.
            # Here we are testing valid-but-weird floats.

if __name__ == "__main__":
    # Allow running directly for print output
    t = TestModelRobustness()
    t.test_noisy_inputs()
    t.test_adversarial_inputs()
