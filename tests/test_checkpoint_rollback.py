import torch
import random
import numpy as np
import os
import shutil
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

def train_for_action(model, target_action, iterations=500):
    trainer = DQNTrainer(model)
    optimizer = trainer.optimizer # Shared ref
    
    for i in range(iterations):
        # Synthetic state
        state = np.random.rand(4).tolist()
        
        # Action choice (random exploration)
        action_idx = random.randint(0, 3)
        
        # Reward: +1 if matches target, -1 otherwise
        reward = 1.0 if action_idx == target_action else -1.0
        
        done = False
        next_state = np.random.rand(4).tolist()
        
        trainer.store_experience(state, action_idx, reward, next_state, done)
        trainer.train_step()
        
def evaluate_bias(model):
    """Returns the most frequent predicted action over 100 random samples."""
    counts = {0:0, 1:0, 2:0, 3:0}
    with torch.no_grad():
        for _ in range(100):
             state = torch.FloatTensor([np.random.rand(4)])
             q = model(state)
             action = torch.argmax(q).item()
             counts[action] += 1
    return max(counts, key=counts.get), counts

def test_checkpoint_rollback():
    print("Starting Checkpoint & Rollback Test...")
    
    # Seeds
    torch.manual_seed(999)
    np.random.seed(999)
    random.seed(999)
    
    os.makedirs("models/test_chk", exist_ok=True)
    path_a = "models/test_chk/checkpoint_A.pth"
    path_b = "models/test_chk/checkpoint_B.pth"
    
    # 1. Train Phase A (Target: UP=0)
    print("\nPhase A: Training for UP (0)...")
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
    train_for_action(model, target_action=0)
    
    torch.save(model.state_dict(), path_a)
    
    pred_a, counts_a = evaluate_bias(model)
    print(f"Checkpoint A saved. Bias: {pred_a} {counts_a}")
    
    if pred_a != 0:
        print("FAILURE: Model failed to learn Phase A target.")
        return

    # 2. Train Phase B (Target: DOWN=1) - CONTINUING from same model
    print("\nPhase B: Retraining for DOWN (1)...")
    train_for_action(model, target_action=1, iterations=500) # Further training
    
    torch.save(model.state_dict(), path_b)
    
    pred_b, counts_b = evaluate_bias(model)
    print(f"Checkpoint B saved. Bias: {pred_b} {counts_b}")
    
    if pred_b != 1:
        print("FAILURE: Model failed to adapt to Phase B target.")
        return

    # 3. Rollback to A
    print("\nPhase C: Rolling back to Checkpoint A...")
    model.load_state_dict(torch.load(path_a))
    
    pred_c, counts_c = evaluate_bias(model)
    print(f"Restored A. Bias: {pred_c} {counts_c}")
    
    if pred_c == 0:
        print("SUCCESS: Rolled back to UP behavior.")
    else:
        print(f"FAILURE: Rollback failed! Expected 0, got {pred_c}.")
        return

    # 4. Rollback to B (just to be sure we can go forward again)
    print("\nPhase D: Rolling forward to Checkpoint B...")
    model.load_state_dict(torch.load(path_b))
    
    pred_d, counts_d = evaluate_bias(model)
    print(f"Restored B. Bias: {pred_d} {counts_d}")
    
    if pred_d == 1:
        print("SUCCESS: Rolled forward to DOWN behavior.")
    else:
        print("FAILURE: Roll forward failed.")
        return

    print("\nOVERALL: Checkpoint/Rollback Verified Successfully.")
    
    # Cleanup
    shutil.rmtree("models/test_chk")

if __name__ == "__main__":
    test_checkpoint_rollback()
