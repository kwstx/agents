import pytest
import torch
import math
from models.decision_model import GridDecisionModel, ModelConfig

class TestGridDecisionModel:
    def test_initialization(self):
        """Test that model initializes with default and custom configs."""
        # Default config
        model = GridDecisionModel()
        assert isinstance(model, torch.nn.Module)
        assert model.fc1.in_features == 4
        assert model.fc3.out_features == 4

        # Custom config
        config = ModelConfig(input_size=10, hidden_size=32, output_size=2)
        model_custom = GridDecisionModel(config)
        assert model_custom.fc1.in_features == 10
        assert model_custom.fc1.out_features == 32
        assert model_custom.fc3.out_features == 2

    def test_forward_pass_shape(self):
        """Test that forward pass produces correct output shape."""
        model = GridDecisionModel()
        batch_size = 5
        input_tensor = torch.rand(batch_size, 4)
        output = model(input_tensor)
        
        assert output.shape == (batch_size, 4)
        assert not torch.isnan(output).any()

    def test_edge_case_inputs(self):
        """Test model behavior with edge case inputs (zeros, ones, negatives)."""
        model = GridDecisionModel()
        
        # All zeros
        zeros = torch.zeros(1, 4)
        out_zeros = model(zeros)
        assert out_zeros.shape == (1, 4)
        
        # All ones
        ones = torch.ones(1, 4)
        out_ones = model(ones)
        assert out_ones.shape == (1, 4)

        # Negatives (should typically be handled by ReLU in first layer, but input itself is valid)
        negatives = torch.tensor([[-1.0, -1.0, -1.0, -1.0]])
        out_neg = model(negatives)
        assert out_neg.shape == (1, 4)

    def test_invalid_dimensions(self):
        """Test that model raises error on wrong input dimensions."""
        model = GridDecisionModel() # input 4
        
        # Wrong input size (e.g., 3 features instead of 4)
        wrong_input = torch.rand(1, 3) 
        with pytest.raises(RuntimeError):
             model(wrong_input)

    def test_nan_inputs_fail_fast(self):
        """Test that model specifically raises error on NaN inputs."""
        model = GridDecisionModel()
        nan_input = torch.tensor([[0.5, float('nan'), 0.2, 0.1]])
        
        # Expecting the model to validate and raise ValueError or similar for NaN
        # PyTorch default behavior is to propagate NaNs, so we expect this to FAIL 
        # until we modify the model to be strict.
        with pytest.raises(ValueError, match="Input contains NaNs"):
            model(nan_input)
