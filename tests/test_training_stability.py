import pytest
import torch
import numpy as np
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

class TestTrainingStability:
    def test_gradient_health(self):
        """
        Verify that gradients are generated, are finite, and are not zero 
        (avoiding vanishing/exploding gradients).
        """
        model = GridDecisionModel()
        trainer = DQNTrainer(model)
        
        # Create a dummy batch
        state = [0.1, 0.2, 0.8, 0.8]
        next_state = [0.1, 0.3, 0.8, 0.8] # Moved up
        action = 0
        reward = 1.0
        done = False
        
        # Fill memory to allow sampling
        for _ in range(trainer.batch_size + 5):
            trainer.store_experience(state, action, reward, next_state, done)
            
        # Initial parameters
        initial_params = [p.clone() for p in model.parameters()]
        
        # Train step
        loss = trainer.train_step()
        
        assert loss > 0, "Loss should be non-zero for unoptimized model"
        
        # Check gradients
        has_nonzero_grad = False
        for name, param in model.named_parameters():
            assert param.grad is not None, f"Parameter {name} has no gradient"
            assert not torch.isnan(param.grad).any(), f"Parameter {name} has NaN gradient"
            assert not torch.isinf(param.grad).any(), f"Parameter {name} has Inf gradient"
            
            grad_norm = param.grad.norm().item()
            # We expect some learning to happen
            if grad_norm > 0.0:
                has_nonzero_grad = True
                
        assert has_nonzero_grad, "Model should have at least some non-zero gradients"

        # Check parameter updates
        params_changed = False
        for p_old, p_new in zip(initial_params, model.parameters()):
            if not torch.equal(p_old, p_new):
                params_changed = True
                break
        assert params_changed, "Parameters should update after optimization step"

    def test_extreme_rewards_stability(self):
        """
        Test stability when encountering extreme reward values.
        """
        model = GridDecisionModel()
        trainer = DQNTrainer(model)
        
        # Extreme reward
        huge_reward = 1e6 
        
        state = [0.5, 0.5, 0.5, 0.5]
        next_state = [0.6, 0.5, 0.5, 0.5]
        
        for _ in range(trainer.batch_size + 1):
            trainer.store_experience(state, 0, huge_reward, next_state, False)
            
        loss = trainer.train_step()
        
        # Loss will be huge, but gradients should ideally not be NaN
        # (Though with valid finite floats, they might be huge but finite)
        assert not math.isnan(loss), "Loss became NaN with huge rewards"
        
        for name, param in model.named_parameters():
             if param.grad is not None:
                assert not torch.isnan(param.grad).any(), f"Gradient became NaN for {name}"
                # Inf check might fail if reward is TRULY huge and overflows float32, 
                # but 1e6 should be fine for float32.

import math
