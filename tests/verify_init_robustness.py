import os
import shutil
import subprocess
import sys
import yaml
import ast
from pathlib import Path

# Configuration
TEST_ROOT = Path("temp_init_tests")
# Determine agent-forge path relative to current python interpreter
if sys.platform == "win32":
    AGENT_FORGE_CMD = str(Path(sys.executable).parent / "agent-forge.exe")
else:
    AGENT_FORGE_CMD = str(Path(sys.executable).parent / "agent-forge")

print(f"Using agent-forge at: {AGENT_FORGE_CMD}")


def setup_test_root():
    if TEST_ROOT.exists():
        try:
            shutil.rmtree(TEST_ROOT)
        except PermissionError:
            print(f"Warning: Could not remove {TEST_ROOT}. Please manually clean up or check permissions.")
            # Try to rename if delete fails or just continue if it's empty enough? 
            # Better to fail fast if we can't clean.
            # On windows, sometimes files are locked.
            pass
    TEST_ROOT.mkdir(parents=True, exist_ok=True)

def run_init(cwd: Path, name: str = "TestAgent"):
    result = subprocess.run(
        [AGENT_FORGE_CMD, "init", name],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=True 
    )
    return result

def verify_files(cwd: Path, name: str = "TestAgent"):
    project_dir = cwd / name
    config_path = project_dir / "agent_config.yaml"
    agent_path = project_dir / "my_agent.py"

    if not project_dir.exists():
        return False, f"Project directory {name} missing"
    if not config_path.exists():
        return False, "agent_config.yaml missing"
    if not agent_path.exists():
        return False, "my_agent.py missing"

    # Verify YAML
    try:
        with open(config_path, "r") as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {e}"

    # Verify Python Syntax
    try:
        with open(agent_path, "r") as f:
            ast.parse(f.read())
    except SyntaxError as e:
        return False, f"Invalid Python syntax: {e}"

    return True, "OK"

def test_empty_folder():
    print("Test: Empty Folder...", end=" ")
    case_dir = TEST_ROOT / "empty"
    case_dir.mkdir()
    
    result = run_init(case_dir)
    if result.returncode != 0:
        print(f"FAILED (Exit Code {result.returncode})")
        print(result.stderr)
        return False

    success, msg = verify_files(case_dir)
    if success:
        print("PASSED")
        return True
    else:
        print(f"FAILED ({msg})")
        return False

def test_existing_files():
    print("Test: Existing Files...", end=" ")
    case_dir = TEST_ROOT / "existing"
    case_dir.mkdir()
    (case_dir / "random.txt").write_text("info")
    
    result = run_init(case_dir)
    if result.returncode != 0:
        print(f"FAILED (Exit Code {result.returncode})")
        return False

    success, msg = verify_files(case_dir)
    if success:
        print("PASSED")
        return True
    else:
        print(f"FAILED ({msg})")
        return False

def test_nested_directories():
    print("Test: Nested Directories...", end=" ")
    case_dir = TEST_ROOT / "deep" / "nested" / "path"
    case_dir.mkdir(parents=True)
    
    result = run_init(case_dir)
    if result.returncode != 0:
        print(f"FAILED (Exit Code {result.returncode})")
        return False
    
    success, msg = verify_files(case_dir)
    if success:
        print("PASSED")
        return True
    else:
        print(f"FAILED ({msg})")
        return False

def test_special_characters():
    print("Test: Special Characters...", end=" ")
    case_dir = TEST_ROOT / "Agents & Stuff!"
    case_dir.mkdir()
    
    # Test valid handling of special chars in CWD, but still use simple name for agent 
    # OR test special chars in Agent Name if supported. 
    # Let's test special chars in CWD first (case_dir has them).
    # And maybe special chars in Name too? "My Agent!"
    
    result = run_init(case_dir, name="Agents & Stuff!")
    if result.returncode != 0:
        print(f"FAILED (Exit Code {result.returncode})")
        return False
    
    success, msg = verify_files(case_dir, name="Agents & Stuff!")
    if success:
        print("PASSED")
        return True
    else:
        print(f"FAILED ({msg})")
        return False

def test_directory_collision():
    print("Test: Directory Collision...", end=" ")
    case_dir = TEST_ROOT / "collision"
    case_dir.mkdir()
    
    # Create the agent directory beforehand
    (case_dir / "TestAgent").mkdir()
    
    result = run_init(case_dir, name="TestAgent")
    
    # Expect failure (Exit code 1)
    if result.returncode != 0:
        # Check output for specific error message
        if "already exists" in result.stdout:
            print("PASSED (Correctly detected collision)")
            return True
        else:
            print(f"FAILED (Job failed but wrong message: {result.stdout})")
            return False
    else:
        print("FAILED (Unexpected Success - overwrote existing dir?)")
        return False

def main():
    setup_test_root()
    
    tests = [
        test_empty_folder,
        test_existing_files,
        test_nested_directories,
        test_special_characters,
        test_directory_collision
    ]
    
    with open("test_results.log", "w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            all_passed = True
            for test in tests:
                print(f"Running {test.__name__}...", flush=True)
                if not test():
                    all_passed = False
                    print(f"FAILED: {test.__name__}", flush=True)
                else:
                    print(f"PASSED: {test.__name__}", flush=True)
            
            if all_passed:
                print("\nAll robustness tests PASSED.")
                sys.exit(0)
            else:
                print("\nSome tests FAILED.")
                sys.exit(1)
        finally:
            sys.stdout = original_stdout

if __name__ == "__main__":
    main()
