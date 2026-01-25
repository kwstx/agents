
import time
import subprocess
import os
import sys

# Benchmarks the "Inner Loop" of development:
# 1. Modify Code (Simulated)
# 2. Run Simulation
# 3. Analyze Results

def benchmark():
    print("--- BENCHMARKING ITERATION SPEED ---")
    
    start_total = time.time()
    
    # 1. Simulate Code Modification
    # We'll just touch the file
    print("[1] Modifying Agent Logic... ", end="")
    t0 = time.time()
    os.utime("agents/learning_agent.py", None)
    t1 = time.time()
    print(f"Done ({t1-t0:.4f}s)")
    
    # 2. Run Simulation (Quick)
    print("[2] Running Simulation (Scenario: benchmark_quick)... ", end="", flush=True)
    t2 = time.time()
    cmd = [sys.executable, "run_scenario.py", "benchmark_quick"]
    # Capture output to avoid spam
    result = subprocess.run(cmd, capture_output=True)
    t3 = time.time()
    
    if result.returncode != 0:
        print(f"FAILED (Return Code {result.returncode})")
        print(result.stderr.decode())
        sys.exit(1)
    else:
        print(f"Done ({t3-t2:.4f}s)")
        
    # 3. Observe Outcomes (Analysis)
    print("[3] Analyzing Results... ", end="", flush=True)
    t4 = time.time()
    # We use analyze_learning.py as a proxy for checking the dashboard/logs
    cmd_analysis = [sys.executable, "scripts/analyze_learning.py"]
    subprocess.run(cmd_analysis, capture_output=True)
    t5 = time.time()
    print(f"Done ({t5-t4:.4f}s)")
    
    end_total = time.time()
    total_duration = end_total - start_total
    
    print("-" * 30)
    print(f"TOTAL LOOP TIME: {total_duration:.2f} seconds")
    
    if total_duration < 10.0:
        print("SUCCESS: Iteration speed is Rapid (< 10s).")
    else:
        print("WARNING: Iteration speed is Slow (> 10s).")

if __name__ == "__main__":
    benchmark()
