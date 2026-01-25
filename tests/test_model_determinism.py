import pytest
import torch
import hashlib
import random
import numpy as np
from models.decision_model import GridDecisionModel

class TestModelDeterminism:
    def _compute_hash(self, tensor: torch.Tensor) -> str:
        """Computes SHA256 hash of tensor data."""
        # Ensure tensor is on CPU and numpy-compatible
        data = tensor.detach().cpu().numpy().tobytes()
        return hashlib.sha256(data).hexdigest()

    def test_deterministic_forward_pass(self):
        """
        Verify that given a fixed seed, the model initialization and 
        forward passes are bit-for-bit identical.
        """
        seed = 42
        
        # Run 1
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        
        model1 = GridDecisionModel()
        input_tensor1 = torch.rand(1, 4)
        output1 = model1(input_tensor1)
        
        hash_input1 = self._compute_hash(input_tensor1)
        hash_output1 = self._compute_hash(output1)
        
        print(f"Run 1 - Input Hash: {hash_input1}")
        print(f"Run 1 - Output Hash: {hash_output1}")

        # Run 2
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        
        model2 = GridDecisionModel()
        input_tensor2 = torch.rand(1, 4)
        output2 = model2(input_tensor2)
        
        hash_input2 = self._compute_hash(input_tensor2)
        hash_output2 = self._compute_hash(output2)
        
        print(f"Run 2 - Input Hash: {hash_input2}")
        print(f"Run 2 - Output Hash: {hash_output2}")

        # Asserts
        assert hash_input1 == hash_input2, "Inputs should be identical with same seed"
        assert hash_output1 == hash_output2, "Outputs should be identical with same seed"
        assert torch.equal(output1, output2), "Output tensors must be strictly equal"
        
        # Verify cross-instantiation consistency
        # Ensure weights are identical
        for p1, p2 in zip(model1.parameters(), model2.parameters()):
            assert torch.equal(p1, p2), "Model parameters must be identical with same seed"

    def test_output_consistency_multiple_passes(self):
        """
        Verify that the SAME model instance produces identical outputs 
        for identical inputs (no internal state drift).
        """
        torch.manual_seed(123)
        model = GridDecisionModel()
        model.eval() # Ensure eval mode (though no dropout/batchnorm used yet)
        
        input_tensor = torch.randn(5, 4)
        
        out1 = model(input_tensor)
        out2 = model(input_tensor)
        out3 = model(input_tensor)
        
        assert torch.equal(out1, out2)
        assert torch.equal(out2, out3)
