
import os
import sys
import yaml
import json
import time
import subprocess
import argparse
from datetime import datetime

MATRIX_FILE = "config/test_matrix.yaml"
CONTROL_FILE = "control.json"

def load_matrix():
    if not os.path.exists(MATRIX_FILE):
        print(f"Error: Matrix file {MATRIX_FILE} not found.")
        sys.exit(1)
    with open(MATRIX_FILE, "r") as f:
        return yaml.safe_load(f)

def run_scenario(scenario_name):
    matrix = load_matrix()
    if scenario_name not in matrix["scenarios"]:
        print(f"Error: Scenario '{scenario_name}' not found in matrix.")
        print(f"Available scenarios: {list(matrix['scenarios'].keys())}")
        sys.exit(1)

    config = matrix["scenarios"][scenario_name]
    print(f"--- Running Scenario: {scenario_name} ---")
    print(f"Description: {config.get('description', '')}")
    print(f"Config: {json.dumps(config, indent=2)}")

    # Prepare command
    cmd = [
        sys.executable,
        "simulation_runner.py",
        "--agent_count", str(config["agent_count"]),
        "--env_size", str(config["env_size"])
    ]
    
    if "agent_type" in config:
        cmd.extend(["--agent_type", config["agent_type"]])

    # Write Control File to START immediately
    control_data = {
        "status": "RUNNING",
        "stress_config": config.get("stress_config", {}),
        "agent_params": config.get("agent_params", {})
    }
    with open(CONTROL_FILE, "w") as f:
        json.dump(control_data, f)
        
    # Launch
    print(f"Launching process: {' '.join(cmd)}")
    with open("logs/latest_run.log", "w") as log_file:
        process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    
    try:
        duration = config.get("duration_s", 10)
        print(f"Running for {duration} seconds...")
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        # Stop safely
        print("Stopping simulation...")
        with open(CONTROL_FILE, "w") as f:
            json.dump({"status": "STOPPED"}, f)
        
        time.sleep(2)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("Done.")

def main():
    parser = argparse.ArgumentParser(description="Run a simulation scenario from the test matrix.")
    parser.add_argument("scenario", help="Name of the scenario to run")
    args = parser.parse_args()
    
    run_scenario(args.scenario)

if __name__ == "__main__":
    main()
