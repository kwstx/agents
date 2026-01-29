import sys
import unittest.mock

def test_missing_server_deps():
    print("--- Simulating Missing Server Dependencies (fastapi/uvicorn) ---")
    # Backup modules
    backup = {k: sys.modules.get(k) for k in ["fastapi", "uvicorn", "agent_forge.core.verifier"]}
    
    # Poison modules
    sys.modules["fastapi"] = None
    sys.modules["uvicorn"] = None
    
    if "agent_forge.core.verifier" in sys.modules:
        del sys.modules["agent_forge.core.verifier"]

    try:
        from agent_forge.core.verifier import Verifier
        print("PASS: Verifier imported successfully without server dependencies.")
    except ImportError as e:
        print(f"FAIL: Verifier blocked by missing dependency: {e}")
    except Exception as e:
        print(f"FAIL: Verifier failed with: {e}")
    finally:
        # Restore (though we don't really need to for this one-shot script)
        pass

def test_missing_cli_deps():
    print("\n--- Simulating Missing CLI Dependencies (rich) ---")
    sys.modules["rich"] = None
    if "agent_forge.cli" in sys.modules:
        del sys.modules["agent_forge.cli"]

    try:
        import agent_forge.cli
        print("FAIL: CLI imported despite missing 'rich'. This implies rich is not a hard dependency (unexpected).")
    except ImportError as e:
        # Check if it was rich that failed
        # Depending on python version, message varies
        print(f"PASS: CLI failed to import as expected (rich is required). Error: {e}")
    except Exception as e:
        print(f"PASS: CLI failed as expected with: {e}")

if __name__ == "__main__":
    test_missing_server_deps()
    test_missing_cli_deps()
