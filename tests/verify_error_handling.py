
import os
import shutil
import subprocess
import sys
import time
import asyncio
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent.parent
CLI_CMD = [sys.executable, "-m", "agent_forge.cli"]

def run_cli_verify(project_path):
    """Runs 'agent-forge verify' in the given path."""
    result = subprocess.run(
        CLI_CMD + ["verify", "--path", str(project_path)],
        capture_output=True,
        text=True,
        cwd=str(project_path)
    )
    return result

def setup_project(name="test_agent"):
    path = Path(name).absolute()
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path

def test_malformed_yaml():
    print("TEST: Malformed YAML...", end=" ")
    proj = setup_project("test_bad_yaml")
    
    # Create bad config
    with open(proj / "agent_config.yaml", "w") as f:
        f.write("agent:\n  name: tab_error\n\tvertical: logistics") # Tab error
        
    # Create valid agent to isolate config error
    with open(proj / "my_agent.py", "w") as f:
        f.write("class MyAgent:\n    def think(self, obs): pass")
        
    res = run_cli_verify(proj)
    
    if res.returncode != 0 and "Invalid YAML" in res.stdout:
        print("PASSED")
    else:
        print(f"FAILED. Return: {res.returncode}\nOut: {res.stdout}")

def test_import_error():
    print("TEST: Import Error...", end=" ")
    proj = setup_project("test_import_error")
    
    # Valid config
    with open(proj / "agent_config.yaml", "w") as f:
        f.write("agent:\n  name: bad_import\n  vertical: logistics")
        
    # Invalid imports
    with open(proj / "my_agent.py", "w") as f:
        f.write("import non_existent_pkg\nclass MyAgent:\n    def think(self, obs): pass")
        
    res = run_cli_verify(proj)
    
    if res.returncode != 0 and "Import Error" in res.stdout:
        print("PASSED")
    else:
        print(f"FAILED. Return: {res.returncode}\nOut: {res.stdout}")

def test_init_crash():
    print("TEST: Init Crash...", end=" ")
    proj = setup_project("test_init_crash")
    
    with open(proj / "agent_config.yaml", "w") as f:
        f.write("agent:\n  name: crashy\n  vertical: logistics")
        
    with open(proj / "my_agent.py", "w") as f:
        f.write("class MyAgent:\n    def __init__(self):\n        raise Exception('BOOM')\n    def think(self, obs): pass")
        
    res = run_cli_verify(proj)
    
    if res.returncode != 0 and "Failed to instantiate MyAgent: BOOM" in res.stdout:
        print("PASSED")
    else:
        print(f"FAILED. Return: {res.returncode}\nOut: {res.stdout}")


async def test_runtime_loop_fail():
    print("TEST: Runtime Loop Crash (Mock)...", end=" ")
    # This requires using the SDK programmatically since CLI run doesn't load custom agents yet
    try:
        from agent_forge.core.runner import HeadlessRunner
        from agent_forge.utils.message_bus import MessageBus
        
        runner = HeadlessRunner()
        # Mock Agent that crashes
        class CrashingAgent:
            def __init__(self, agent_id):
                self.agent_id = agent_id
            async def start(self): pass
            async def stop(self): pass
            async def add_task(self, task):
                # Simulate crash in loop
                raise RuntimeError("Loop Crash")
        
        runner.agents = [CrashingAgent("CrashBot")]
        
        # Start and expect it to NOT crash the main process, or handle it
        try:
            await runner.start()
        except RuntimeError as e:
            if "Loop Crash" in str(e):
                print("PASSED (Caught Exception)")
                return
        
        print("FAILED (Exception not raised/caught)")
        
    except ImportError:
         print("SKIPPED (Classes not found)")

if __name__ == "__main__":
    test_malformed_yaml()
    test_import_error()
    test_init_crash()
    asyncio.run(test_runtime_loop_fail())
    
    # Cleanup
    for d in ["test_bad_yaml", "test_import_error", "test_init_crash"]:
        if Path(d).exists():
            shutil.rmtree(d)
