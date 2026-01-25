import pytest
import torch
import copy
from agents.learning_agent import LearningGridAgent
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer
from agents.hooks import DQNTrainHook
from environments.grid_world import GridWorld
from utils.message_bus import MessageBus

class TestAgentIsolation:
    def test_parameter_isolation(self):
        """Verify that two agents possess distinct model parameters in memory."""
        config = ModelConfig()
        
        # Agent A
        model_a = GridDecisionModel(config)
        trainer_a = DQNTrainer(model_a, config)
        
        # Agent B
        model_b = GridDecisionModel(config)
        trainer_b = DQNTrainer(model_b, config)
        
        # Check distinct objects
        assert model_a is not model_b
        assert trainer_a is not trainer_b
        
        # Check distinct tensors
        for p_a, p_b in zip(model_a.parameters(), model_b.parameters()):
            assert p_a is not p_b
            # They might have same values if initialized identically (e.g. fixed seed),
            # but they must be different objects.
            assert id(p_a) != id(p_b)

    def test_training_isolation(self):
        """Verify that training Agent A does not affect Agent B."""
        env = GridWorld(size=5)
        bus = MessageBus()
        config = ModelConfig(learning_rate=0.1) # High LR to ensure visible change
        
        # Agent A Setup
        model_a = GridDecisionModel(config)
        trainer_a = DQNTrainer(model_a, config)
        hook_a = DQNTrainHook(trainer_a)
        agent_a = LearningGridAgent("Agent-A", bus, env, model_a, hooks=[hook_a])
        
        # Agent B Setup
        model_b = GridDecisionModel(config)
        trainer_b = DQNTrainer(model_b, config)
        hook_b = DQNTrainHook(trainer_b)
        agent_b = LearningGridAgent("Agent-B", bus, env, model_b, hooks=[hook_b])
        
        # Snapshot B's weights
        initial_weights_b = [p.clone() for p in model_b.parameters()]
        initial_weights_a = [p.clone() for p in model_a.parameters()]
        
        # Train Agent A manually for a step
        # Create dummy experience
        state = [0.1, 0.1, 0.5, 0.5]
        next_state = [0.2, 0.1, 0.5, 0.5]
        
        # Fill buffer for A
        for _ in range(trainer_a.batch_size + 1):
            trainer_a.store_experience(state, 0, 10.0, next_state, False)
            
        # Trigger training for A
        loss = trainer_a.train_step()
        assert loss > 0
        
        # Verify A changed
        a_changed = False
        for p_old, p_new in zip(initial_weights_a, model_a.parameters()):
            if not torch.equal(p_old, p_new):
                a_changed = True
                break
        assert a_changed, "Agent A should have updated weights"
        
        # Verify B did NOT change
        for p_old, p_curr in zip(initial_weights_b, model_b.parameters()):
            assert torch.equal(p_old, p_curr), "Agent B's weights changed! Isolation breached."
            
        print("\nSuccess: Agent A trained, Agent B remained frozen.")
