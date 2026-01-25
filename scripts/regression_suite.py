
import sys
import subprocess
import os
import time

def run_step(name, cmd, cwd=None, fatal=True):
    print(f"--- RUNNING: {name} ---")
    start = time.time()
    result = subprocess.run(cmd, cwd=cwd, shell=True) # Check shell=True for windows cmd handling
    end = time.time()
    
    if result.returncode == 0:
        print(f"PASS: {name} ({end-start:.2f}s)")
        return True
    else:
        print(f"FAIL: {name} (Return Code {result.returncode})")
        if fatal:
            sys.exit(1)
        return False

def clean_db():
    if os.path.exists("data/memory.db"):
        try:
            os.remove("data/memory.db")
            # Recreate dir if missing
            if not os.path.exists("data"):
               os.mkdir("data")
        except:
            pass

def main():
    print("=== STARTING REGRESSION SUITE ===")
    start_total = time.time()
    
    # 1. Unit Tests
    # Note: We need to ensure we are in the correct env.
    # Assuming 'python' is the correct interpreter.
    run_step("Unit Tests", "python -m pytest tests/")
    
    # 2. Integration: Collaboration
    clean_db()
    run_step("Sim: Coordination Test", "python run_scenario.py coordination_test")
    run_step("Verify: Collaboration", "python scripts/verify_collaboration.py")
    
    # 3. Integration: Resilience
    clean_db()
    run_step("Sim: Communication Stress", "python run_scenario.py communication_stress")
    run_step("Verify: Resilience", "python scripts/verify_resilience.py")
    
    end_total = time.time()
    print(f"=== ALL TESTS PASSED ({end_total-start_total:.2f}s) ===")

if __name__ == "__main__":
    main()
