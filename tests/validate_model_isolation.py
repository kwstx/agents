import torch
import random
import numpy as np
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

def validate_model_isolation():
    print("Starting Model Isolation Test...")
    
    # Setup
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
    trainer = DQNTrainer(model)
    
    # Synthetic Task: "Always Choose Action 3 (RIGHT)"
    # State is random noise [0, 1]
    
    initial_loss = None
    final_loss = None
    
    iterations = 1000
    
    print(f"Training for {iterations} iterations...")
    
    for i in range(iterations):
        # Generate random state
        state = np.random.rand(4).tolist()
        
        # Random action taken (exploration) OR optimal action
        action_idx = random.randint(0, 3)
        
        # Reward Logic: +1 if Action 3, -1 otherwise
        reward = 1.0 if action_idx == 3 else -1.0
        
        # Next state (irrelevant for this simple bandit-like task, but needed for DQN)
        next_state = np.random.rand(4).tolist()
        done = False # Continuous task
        
        trainer.store_experience(state, action_idx, reward, next_state, done)
        
        loss = trainer.train_step()
        
        if i == 100:
            initial_loss = loss
        if i > 0 and i % 200 == 0:
            print(f"Iter {i}: Loss={loss:.6f}")
            
    final_loss = loss
    
    print(f"\nInitial Loss (approx): {initial_loss}")
    print(f"Final Loss: {final_loss}")
    
    if final_loss < initial_loss:
        print("SUCCESS: Loss has decreased.")
    else:
        print("WARNING: Loss did not decrease significantly.")
        
    # Verification: Check Prediction Accuracy
    print("\nVerifying Predictions...")
    correct = 0
    test_samples = 100
    
    with torch.no_grad():
        for _ in range(test_samples):
            state = torch.FloatTensor([np.random.rand(4)])
            q_values = model(state)
            predicted_action = torch.argmax(q_values).item()
            
            if predicted_action == 3:
                correct += 1
                
    accuracy = correct / test_samples
    print(f"Accuracy (Should pick Action 3): {accuracy*100:.1f}%")
    
    if accuracy > 0.9:
        print("SUCCESS: Model converged to optimal action.")
    else:
        print("FAILURE: Model did not converge to optimal action.")

if __name__ == "__main__":
    validate_model_isolation()
