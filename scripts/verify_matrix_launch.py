
import csv
import sys
import os

METRICS_FILE = "logs/learning_metrics.csv"

def verify_crowded():
    print("Verifying 'crowded' scenario metrics...")
    if not os.path.exists(METRICS_FILE):
        print("FAIL: Metrics file not found.")
        sys.exit(1)
        
    agents = set()
    with open(METRICS_FILE, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        if "agent_id" not in header:
            print("FAIL: No agent_id in header")
            sys.exit(1)
            
        idx = header.index("agent_id")
        for row in reader:
            if row:
                agents.add(row[idx])
                
    print(f"Agents found in logs: {agents}")
    expected_agents = {"Agent-1", "Agent-2", "Agent-3", "Agent-4", "Agent-5"}
    
    # Note: If previous runs are in the same file, we need to be careful?
    # The runner appends.
    # But ideally, we should see at least these agents.
    
    if expected_agents.issubset(agents):
        print("SUCCESS: Found all expected agents for 'crowded' scenario.")
    else:
        print(f"FAIL: Missing agents. Expected {expected_agents}")
        sys.exit(1)

if __name__ == "__main__":
    verify_crowded()
