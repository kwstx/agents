
import subprocess
import time
import json
import os
import csv
import sys

CONTROL_FILE = "control.json"
METRICS_FILE = "logs/learning_metrics.csv"
EVENT_LOG = "logs/simulation_events.jsonl"

def setup():
    # Reset logs
    if os.path.exists(METRICS_FILE):
        os.remove(METRICS_FILE)
    if os.path.exists(EVENT_LOG):
        os.remove(EVENT_LOG)
        
    # Write initial control
    with open(CONTROL_FILE, "w") as f:
        json.dump({"status": "RUNNING", "stress_config": {}, "agent_params": {"epsilon": 0.5}}, f)

def run_sim():
    print("Starting simulation runner...")
    # Capture output to see what's wrong
    process = subprocess.Popen([sys.executable, "simulation_runner.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("Running for 5 seconds...")
    time.sleep(5)
    
    print("Stopping simulation...")
    with open(CONTROL_FILE, "w") as f:
        json.dump({"status": "STOPPED"}, f)
        
    time.sleep(2)
    process.terminate()
    try:
        outs, errs = process.communicate(timeout=2)
        print("--- Simulation STDOUT ---")
        print(outs)
        print("--- Simulation STDERR ---")
        print(errs)
    except subprocess.TimeoutExpired:
        process.kill()
        outs, errs = process.communicate()
        print("--- Simulation STDOUT (Killed) ---")
        print(outs)
        print("--- Simulation STDERR (Killed) ---")
        print(errs)
    print("Simulation process ended.")

def verify_output():
    print("Verifying metrics...")
    if not os.path.exists(METRICS_FILE):
        print("FAIL: Metrics file not found.")
        return False
        
    api_agents = set()
    rows = 0
    with open(METRICS_FILE, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Expected: timestamp, step, agent_id, epsilon, reward
        if "agent_id" not in header:
             print(f"FAIL: agent_id missing in header: {header}")
             return False
             
        agent_idx = header.index("agent_id")
        for row in reader:
            if row:
                api_agents.add(row[agent_idx])
                rows += 1
    
    print(f"Found {rows} metric rows for agents: {api_agents}")
    
    if "Agent-Alpha" in api_agents and "Agent-Beta" in api_agents:
        print("SUCCESS: Both agents logged data.")
        return True
    else:
        print("FAIL: Missing agents.")
        return False

if __name__ == "__main__":
    setup()
    run_sim()
    result = verify_output()
    sys.exit(0 if result else 1)
