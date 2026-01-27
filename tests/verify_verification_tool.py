import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Configuration
TEST_ROOT = Path("temp_verify_tests")
# Determine agent-forge path relative to current python interpreter
if sys.platform == "win32":
    AGENT_FORGE_CMD = str(Path(sys.executable).parent / "agent-forge.exe")
else:
    AGENT_FORGE_CMD = str(Path(sys.executable).parent / "agent-forge")

def setup_test_root():
    if TEST_ROOT.exists():
        try:
            shutil.rmtree(TEST_ROOT)
        except Exception:
            pass # Best effort
    TEST_ROOT.mkdir(parents=True, exist_ok=True)

def create_agent(path: Path, config: str = None, code: str = None):
    path.mkdir(parents=True, exist_ok=True)
    
    if config is not None:
        with open(path / "agent_config.yaml", "w") as f:
            f.write(config)
            
    if code is not None:
        with open(path / "my_agent.py", "w") as f:
            f.write(code)

def run_verify(cwd: Path):
    result = subprocess.run(
        [AGENT_FORGE_CMD, "verify"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=True 
    )
    return result

def test_correct_agent():
    print("Test: Correct Agent...", end=" ")
    case_dir = TEST_ROOT / "valid"
    
    config = """
agent:
  name: ValidAgent
  vertical: logistics
"""
    code = """
class MyAgent:
    def process_task(self, task):
        pass
"""
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode == 0 and "VERIFICATION SUCCESSFUL" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED (Exit {result.returncode})")
        print(result.stdout)
        return False

def test_missing_config():
    print("Test: Missing Config...", end=" ")
    case_dir = TEST_ROOT / "missing_config"
    code = "class MyAgent: pass"
    create_agent(case_dir, config=None, code=code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "Missing required files" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED (Unexpected Success or wrong error)")
        print(result.stdout)
        return False

def test_invalid_yaml():
    print("Test: Invalid YAML...", end=" ")
    case_dir = TEST_ROOT / "invalid_yaml"
    config = "agent: [unclosed list"
    code = "class MyAgent: pass"
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "Invalid YAML" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED")
        print(result.stdout)
        return False

def test_missing_class():
    print("Test: Missing Class...", end=" ")
    case_dir = TEST_ROOT / "no_class"
    config = "agent:\n  name: NoClass\n  vertical: log"
    code = "def foo(): pass"
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "must define a class named 'MyAgent'" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED")
        print(result.stdout)
        return False

def test_missing_method():
    print("Test: Missing Method...", end=" ")
    case_dir = TEST_ROOT / "no_method"
    config = "agent:\n  name: NoMethod\n  vertical: log"
    code = "class MyAgent:\n    pass"
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "must implement 'process_task'" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED")
        print(result.stdout)
        return False

def test_syntax_error():
    print("Test: Syntax Error...", end=" ")
    case_dir = TEST_ROOT / "syntax_error"
    config = "agent:\n  name: SyntaxErr\n  vertical: log"
    code = "class MyAgent:\n    def process_task(self): print('unclosed string"
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "Syntax Error" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED")
        print(result.stdout)
        return False

def test_runtime_init_error():
    print("Test: Runtime Init Error...", end=" ")
    case_dir = TEST_ROOT / "init_error"
    config = "agent:\n  name: InitErr\n  vertical: log"
    code = """
class MyAgent:
    def __init__(self):
        raise ValueError("Boom")
    def process_task(self): pass
"""
    create_agent(case_dir, config, code)
    
    result = run_verify(case_dir)
    if result.returncode != 0 and "Failed to instantiate MyAgent" in result.stdout:
        print("PASSED")
        return True
    else:
        print(f"FAILED")
        print(result.stdout)
        return False

def main():
    setup_test_root()
    
    tests = [
        test_correct_agent,
        test_missing_config,
        test_invalid_yaml,
        test_missing_class,
        test_missing_method,
        test_syntax_error,
        test_runtime_init_error
    ]
    
    with open("test_verify_results.log", "w") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            print(f"Using agent-forge: {AGENT_FORGE_CMD}")
            all_passed = True
            for test in tests:
                print(f"Running {test.__name__}...", flush=True)
                if not test():
                    all_passed = False
                    print(f"FAILED: {test.__name__}", flush=True)
                else:
                    print(f"PASSED: {test.__name__}", flush=True)
            
            if all_passed:
                print("\nAll verification tests PASSED.")
                sys.exit(0)
            else:
                print("\nSome tests FAILED.")
                sys.exit(1)
        finally:
            sys.stdout = original_stdout

if __name__ == "__main__":
    main()
