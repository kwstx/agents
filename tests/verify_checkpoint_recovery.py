import pytest
import torch
import os
import shutil
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

TEMP_DIR = "tests_temp_checkpoints"

class TestCheckpointRecovery:
    
    @classmethod
    def setup_class(cls):
        os.makedirs(TEMP_DIR, exist_ok=True)
        
    @classmethod
    def teardown_class(cls):
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)

    def test_save_and_reload(self):
        """Verify that a saved model can be reloaded and state is identical."""
        path = os.path.join(TEMP_DIR, "test_model.pth")
        
        # 1. Create and modify a model
        model_orig = GridDecisionModel()
        # Manually modify weights to ensure we aren't just testing default init
        with torch.no_grad():
            model_orig.fc1.weight.add_(0.5)
            
        trainer_orig = DQNTrainer(model_orig)
        trainer_orig.save_model(path)
        
        # 2. Load into fresh model
        model_new = GridDecisionModel()
        trainer_new = DQNTrainer(model_new)
        loaded = trainer_new.load_model(path)
        
        assert loaded is True, "Model should report successful load"
        
        # 3. Compare parameters
        for p_orig, p_new in zip(model_orig.parameters(), model_new.parameters()):
            assert torch.equal(p_orig, p_new), "Parameters mismatch after reload"
            
        # 4. Compare outputs
        input_tensor = torch.rand(1, 4)
        out_orig = model_orig(input_tensor)
        out_new = model_new(input_tensor)
        assert torch.equal(out_orig, out_new), "Outputs mismatch after reload"

    def test_missing_file_handling(self):
        """Verify handling of missing checkpoint files."""
        model = GridDecisionModel()
        trainer = DQNTrainer(model)
        
        path = os.path.join(TEMP_DIR, "non_existent.pth")
        loaded = trainer.load_model(path)
        
        assert loaded is False, "Should return False for missing file"

    def test_corrupt_file_handling(self):
        """Verify explicitly that corrupt files raise an error or are handled."""
        path = os.path.join(TEMP_DIR, "corrupt.pth")
        
        # Write garbage
        with open(path, "w") as f:
            f.write("This is not a zip file or a torch checkpoint")
            
        model = GridDecisionModel()
        trainer = DQNTrainer(model)
        
        # PyTorch usually raises reasonable errors (e.g. UnpicklingError or generic RuntimeError)
        # We want to ensure it DOES fail, not silently swallow it if we had a bare except.
        # Check `trainer.py` implementation: it does NOT have a try/except around torch.load.
        # So we expect an exception.
        
        with pytest.raises(Exception): # Accept any exception from torch serialization
            trainer.load_model(path)
