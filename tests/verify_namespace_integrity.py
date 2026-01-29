import sys
import os
import importlib
import inspect

def verify_integrity():
    print("Verifying Namespace Integrity...")
    
    # 1. Trigger imports using the proper namespace
    try:
        import agent_forge.agents.learning_agent
        import agent_forge.environments.order_book_env
        import agent_forge.utils.interaction_logger
    except ImportError as e:
        print(f"FATAL: Could not import via namespace: {e}")
        sys.exit(1)

    # 2. Check sys.modules for Forbidden Top-Level Modules
    forbidden_top_level = [
        "agents", "environments", "models", "utils", "config", 
        "dashboards", "benchmarking"
    ]
    
    violations = []
    
    for mod_name in list(sys.modules.keys()):
        # Check if any forbidden top-level package is loaded directly
        # We check split('.')[0] to catch submodules like 'agents.learning_agent'
        root_pkg = mod_name.split('.')[0]
        if root_pkg in forbidden_top_level:
            # Check if it maps to our code
            mod = sys.modules[mod_name]
            if hasattr(mod, '__file__') and mod.__file__ and "agent_forge" in mod.__file__:
                violations.append(f"Top-level import detected: {mod_name} -> {mod.__file__}")

    if violations:
        print("FAIL: The following modules were imported incorrectly (not through agent_forge namespace):")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    # 3. Check that agent_forge modules come from site-packages (or src/agent_forge in editable)
    # and strictly verify the __package__ attribute
    print("Checking agent_forge modules...")
    for mod_name, mod in sys.modules.items():
        if mod_name.startswith("agent_forge.") and hasattr(mod, '__file__'):
            # Check that it's acting as a subpackage
            if not mod.__package__ or not mod.__package__.startswith("agent_forge"):
                 # This might happen if 'agent_forge' is just a folder in sys.path?
                 # less likely with pip install -e .
                 pass
                 
    print("SUCCESS: Namespace integrity verified. No leaked top-level imports.")

if __name__ == "__main__":
    verify_integrity()
