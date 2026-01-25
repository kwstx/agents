
import csv
import sys
import os
import collections

METRICS_FILE = "logs/learning_metrics.csv"

def analyze_learning():
    if not os.path.exists(METRICS_FILE):
        print("FAIL: Metrics file not found.")
        sys.exit(1)
        
    # Read metrics
    # Format: timestamp, step, agent_id, epsilon, reward
    # Logic:
    # 1. Group rewards by windows of steps (e.g. every 100 steps)
    # 2. Or, more simply, check if average reward in last 20% of run > average reward in first 20%.
    
    rows = []
    with open(METRICS_FILE, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row:
                rows.append(row)
                
    if not rows:
        print("FAIL: No metrics found.")
        sys.exit(1)
        
    rewards = [float(r[4]) for r in rows]
    epsilons = [float(r[3]) for r in rows]
    steps = [int(r[1]) for r in rows]
    
    total_steps = len(rows)
    print(f"Total Data Points: {total_steps}")
    print(f"Initial Epsilon: {epsilons[0]}")
    print(f"Final Epsilon: {epsilons[-1]}")
    
    if epsilons[-1] >= epsilons[0]:
         print("WARNING: Epsilon did not decay. Training loop might be broken.")
         # Not strictly a fail if using constant epsilon, but we expect decay.
    
    # Simple Windowed Analysis
    window_size = max(1, total_steps // 5) # 5 chunks
    
    first_chunk = rewards[:window_size]
    last_chunk = rewards[-window_size:]
    
    avg_first = sum(first_chunk) / len(first_chunk)
    avg_last = sum(last_chunk) / len(last_chunk)
    
    print(f"Average Reward (First {window_size} steps): {avg_first:.4f}")
    print(f"Average Reward (Last {window_size} steps):  {avg_last:.4f}")
    
    improvement = avg_last - avg_first
    print(f"Improvement: {improvement:.4f}")
    
    if improvement > 0:
        print("SUCCESS: Performance improved.")
    else:
        print("WARNING: Performance flat or regressed. (May need longer run or hyperparameter tuning)")
        # In MVP, learning is hard. Fail if catastrophic? 
        # For now, just reporting.
        
    # Calculate Success Rate (if reward > 0 means goal?) 
    # Current reward: +10 for goal, -0.1 per step.
    # So heavily negative means wandering. Positive means hitting goals quickly.
    
    success_count_first = len([r for r in first_chunk if r > 0])
    success_count_last = len([r for r in last_chunk if r > 0])
    
    print(f"Positive Reward Events (First): {success_count_first}")
    print(f"Positive Reward Events (Last):  {success_count_last}")

if __name__ == "__main__":
    analyze_learning()
