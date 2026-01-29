import subprocess
import os
import shutil
import sys
import time

def run_command(cmd, cwd=None):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result

def main():
    print("=== CLI Regression Test ===")
    
    # 1. Test Help
    print("\n[1] Testing Help command")
    cmd = [sys.executable, "-m", "agent_forge.cli", "--help"]
    result = run_command(cmd)
    
    if result.returncode != 0:
        print("FAIL: Help command returned non-zero exit code")
        print(result.stderr)
        return
    else:
        print("PASS: Help command executed successfully")
        # Check for expected keywords - note: rich might format output, simple text check
        output = result.stdout
        # Typer/Click usually prints to stdout for help
        if "Agent Forge" in output or "verify" in output:
             print("PASS: Help output contains expected keywords")
        else:
             print("WARNING: Help output might be missing keywords or captured incorrectly due to formatting.")
             print(f"Output length: {len(output)}")

    # 2. Test Init
    test_dir = "temp_cli_test_agent"
    # Ensure cleanup
    if os.path.exists(test_dir):
        try:
            shutil.rmtree(test_dir)
        except OSError as e:
            print(f"Warning: Could not clean up existing directory {test_dir}: {e}")
        
    print(f"\n[2] Testing Init command: {test_dir}")
    cmd_init = [sys.executable, "-m", "agent_forge.cli", "init", test_dir]
    result_init = run_command(cmd_init)
    
    if result_init.returncode != 0:
         print(f"FAIL: Init command failed: {result_init.stderr}")
         # Attempt to verify what happened
         print(f"Stdout: {result_init.stdout}")
         return
    else:
         print("PASS: Init command successful")
         
    if os.path.exists(os.path.join(test_dir, "agent_config.yaml")) and \
       os.path.exists(os.path.join(test_dir, "my_agent.py")):
        print("PASS: Project files created successfully")
    else:
        print("FAIL: Project files missing")
        return

    # 3. Test Verify
    print(f"\n[3] Testing Verify command in {test_dir}")
    cmd_verify = [sys.executable, "-m", "agent_forge.cli", "verify"]
    # We need to run this relative to the test_dir or pass path
    # CLI default path is "."
    result_verify = run_command(cmd_verify, cwd=test_dir)
    
    print(f"Verify Output:\n{result_verify.stdout}")
    if result_verify.stderr:
        print(f"Verify Stderr:\n{result_verify.stderr}")
    
    if result_verify.returncode == 0:
        print("PASS: Verify command successful")
    else:
        print(f"FAIL: Verify command returned {result_verify.returncode}")

    # 4. Test Run (Headless)
    print(f"\n[4] Testing Run command (Headless) in {test_dir}")
    # run without --ui calls verify
    cmd_run = [sys.executable, "-m", "agent_forge.cli", "run"]
    result_run = run_command(cmd_run, cwd=test_dir)
    
    if result_run.returncode == 0:
        print("PASS: Run command successful")
    else:
        print(f"FAIL: Run command returned {result_run.returncode}")
        print(f"Output:\n{result_run.stdout}")
        print(f"Stderr:\n{result_run.stderr}")

    # Cleanup 3 and 4
    # We keep the directory for step 5

    # 5. Test Run with UI
    print(f"\n[5] Testing Run command (UI) in {test_dir}")
    
    cmd_ui = [sys.executable, "-m", "agent_forge.cli", "run", "--ui"]
    print("Starting UI process...")
    # subprocess.Popen needed for non-blocking
    proc = subprocess.Popen(
        cmd_ui,
        cwd=test_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait a bit for startup
        time.sleep(5)
        if proc.poll() is None:
            print("PASS: UI process started and is running")
            # We could try to curl localhost:3000 here if we want to be thorough
        else:
            print(f"FAIL: UI process exited early with code {proc.returncode}")
            # Capture output
            out, err = proc.communicate()
            print(f"Stdout: {out}")
            print(f"Stderr: {err}")
    finally:
        # Clean shutdown
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("UI process terminated")

    # Final Cleanup
    if os.path.exists(test_dir):
        try:
            shutil.rmtree(test_dir)
            print("\nCleanup successful")
        except OSError as e:
            print(f"\nCleanup failed: {e}")

if __name__ == "__main__":
    main()
