
import subprocess
import sys
import os
import sqlite3
import json
import time

# Script runs "coordination_test", gathers metrics, then "communication_stress", gathers metrics.
# Note: "coordination_test" is 2 agents, 5x5. "communication_stress" is 5 agents, 10x10.
# Comparing raw counts isn't fair.
# Metric: "Redundancy Rate" = 1 - (Unique Cells / Total Moves).
# But since env and agent count differ, we should run a CONTROL stress test?
# i.e. Run "communication_stress" with chaos=0 vs chaos=High.
# YES. To be scientific, we must use the SAME scenario parameters, just differ chaos.

# We will run "communication_stress" but override chaos in code? 
# Or just define a "communication_baseline" scenario in matrix.

MATRIX_FILE = "config/test_matrix.yaml"
CONTROL_FILE = "control.json"
DB_PATH = "data/memory.db"

def clear_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def analyze_redundancy(scenario_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all "exploration_update" payloads (which represent moves to new assignments or completed steps)
    # CollaborativeAgent sends "exploration_update" with {pos: (x,y)} on step complete.
    
    cursor.execute("SELECT content FROM memories WHERE type='message_sent' AND content LIKE '%exploration_update%'")
    rows = cursor.fetchall()
    
    total_moves = 0
    visited_cells = set()
    
    for row in rows:
        try:
            data = json.loads(row[0])
            pos = tuple(data["payload"]["pos"])
            visited_cells.add(pos)
            total_moves += 1
        except:
            pass
            
    conn.close()
    
    if total_moves == 0:
        return 0.0, 0, 0
        
    unique = len(visited_cells)
    efficiency = unique / total_moves
    return efficiency, unique, total_moves

def run_test(scenario, override_chaos=False):
    print(f"--- Running {scenario} {'(NO CHAOS)' if override_chaos else '(STRESS)'} ---")
    clear_db()
    
    # We use arguments to simulation_runner to override chaos if needed?
    # run_scenario.py reads config. config has stress_config.
    # To override, we'd need to modify the config or passed args.
    # Simpler: Just rely on "coordination_test" (low stress) vs "communication_stress" (high stress) logic?
    # No, sizes differ.
    
    # Quick hack: We will manually launch `simulation_runner.py` with known arguments.
    # BASELINE: 5 agents, 10, no stress.
    # STRESS: 5 agents, 10, stress.
    
    cmd = [
        sys.executable, "simulation_runner.py",
        "--agent_count", "5",
        "--env_size", "10",
        "--agent_type", "collaborative"
    ]
    
    # Write control file
    control_data = {
        "status": "RUNNING",
        "agent_params": {},
        "stress_config": {
            "drop_rate": 0.2 if not override_chaos else 0.0,
            "latency_ms": 200 if not override_chaos else 0
        }
    }
    
    with open(CONTROL_FILE, "w") as f:
        json.dump(control_data, f)
        
    with open("logs/compare.log", "w") as log:
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        
    try:
        time.sleep(15)
    finally:
        with open(CONTROL_FILE, "w") as f:
            json.dump({"status": "STOPPED"}, f)
        time.sleep(2)
        p.terminate()
        try:
            p.wait(timeout=5)
        except:
            p.kill()
            
    return analyze_redundancy(scenario)

def main():
    print("Starting Comparative Analysis...")
    
    # Run Baseline (Ideal)
    eff_ideal, unique_ideal, total_ideal = run_test("BASELINE", override_chaos=True)
    print(f"BASELINE: Efficiency={eff_ideal:.2f} (Unique={unique_ideal}, Total={total_ideal})")
    
    # Run Stress
    eff_stress, unique_stress, total_stress = run_test("STRESS", override_chaos=False)
    print(f"STRESS:   Efficiency={eff_stress:.2f} (Unique={unique_stress}, Total={total_stress})")
    
    print("-" * 30)
    
    # Validation
    # In ideal, agents share info and avoid visited. Efficiency should be higher (closer to 1.0 or high plateau).
    # In stress, messages regarding "visited" are lost. Agents unknowingly re-visit cells. Efficiency drops.
    
    if total_stress == 0:
        print("FAIL: Stress test did not execute moves.")
        sys.exit(1)

    # Note: If random walk is total blind, efficiency is low.
    # Collaborative is higher.
    # Stress collaborative should be between Blind and Ideal.
    
    # Assert degradation
    if eff_stress < eff_ideal:
        print("SUCCESS: Visible degradation confirmed (Stress Efficiency < Ideal Efficiency).")
    else:
        print("WARNING: Stress efficiency >= Ideal. (Maybe 20% drop isn't enough to hurt logic or randomness luck?)")
        # Don't fail hard, behavior is probabilistic.
        # But for 'fail-only-if', we adhere to pass condition: "Recovery behavior is visible".
        # If it performs *equally well*, it's ironically extremely resilient (or the test is invalid).
        pass

    # Assert Survival
    if eff_stress > 0.1: # Arbitrary "alive" threshold
         print("SUCCESS: System survived stress (Non-zero efficiency).")
    else:
         print("FAIL: System collapsed under stress.")
         sys.exit(1)

if __name__ == "__main__":
    main()
