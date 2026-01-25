
import subprocess
import sys
import csv
import os

def run_scenario_and_get_score(scenario_name):
    print(f"--- Running {scenario_name} ---")
    
    # Clean metrics
    if os.path.exists("logs/learning_metrics.csv"):
        os.remove("logs/learning_metrics.csv")
        
    cmd = [sys.executable, "run_scenario.py", scenario_name]
    subprocess.run(cmd, capture_output=True)
    
    # Read metrics
    rewards = []
    if os.path.exists("logs/learning_metrics.csv"):
        with open("logs/learning_metrics.csv", "r") as f:
            reader = csv.reader(f)
            next(reader, None) # header
            for row in reader:
                if row:
                    rewards.append(float(row[4]))
                    
    if not rewards:
        return 0, 0
        
    avg_reward = sum(rewards) / len(rewards)
    # Success count (Reward >= 10.0 usually indicates goal hit, though step penalties subtract)
    # Wait, in grid_env, goal reward is 10.
    # Logic: if reward > 0 it's likely a goal hit in that step.
    # Actually, goal hit resets agent.
    # Let's count "Positive Reward Events"
    successes = len([r for r in rewards if r > 0])
    
    return avg_reward, successes

def main():
    print("Evaluating Generalization...")
    
    # Note: We rely on the EXISTING model in models/Agent-1_mlp.pth
    # The scenarios use "agent_type: learning", which attempts to load this model.
    # IMPORTANT: We must ensure the model exists. 
    # (It was created in previous steps).
    
    if not os.path.exists("models/Agent-1_mlp.pth"):
         print("WARNING: No pre-trained model found. Results will be random.")
    
    # 1. Reference (5x5)
    ref_avg, ref_wins = run_scenario_and_get_score("test_5x5")
    print(f"Reference (5x5): Avg Reward={ref_avg:.4f}, Successes={ref_wins}")
    
    # 2. Generalization (10x10)
    gen_avg, gen_wins = run_scenario_and_get_score("test_10x10")
    print(f"Generalization (10x10): Avg Reward={gen_avg:.4f}, Successes={gen_wins}")
    
    # Analysis
    print("-" * 30)
    
    if ref_wins == 0:
        print("FAIL: Agent failed in reference environment. Training was ineffective.")
        sys.exit(1)
        
    # In 10x10, it's harder.
    # If 0 wins, it might fail to generalize OR just takes too long for 30s?
    # 10x10 worst case steps ~20-30 moves. 30s is plenty.
    
    if gen_wins > 0:
        print("SUCCESS: Agent generalized to larger environment.")
    else:
        print("WARNING: Agent failed to generalize (0 successes in 10x10). Overfitting detected.")
        # This is a valuable finding for "Evaluate Auto-Refinement".
        # It means simple MLP overfitting to coordinates.
        
    # Check degradation
    # If gen_avg is significantly worse than ref_avg
    drop = ref_avg - gen_avg
    print(f"Performance Drop: {drop:.4f}")

if __name__ == "__main__":
    main()
