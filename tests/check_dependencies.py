import ast
import os
import sys

ALLOWED_PREFIXES = {
    "core", 
    "agents.base_agent", 
    "environments.base_env", 
    "utils", 
    "agents.agent_registry",
    "environments.env_registry",
}

# Standard library modules (approximate list or just allow everything that isn't project local)
# For simplicity, we flag imports that start with 'agents.' or 'environments.' but aren't in allowed list.

def get_imports(filepath):
    """Parses a python file and returns a list of imported module names."""
    with open(filepath, "r") as f:
        tree = ast.parse(f.read(), filename=filepath)
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def check_file(filepath):
    print(f"Checking {filepath}...")
    imports = get_imports(filepath)
    violations = []
    for imp in imports:
        # Check against project structure restrictions
        # Vertical agents shouldn't import other vertical agents
        if imp.startswith("agents.") and imp != "agents.base_agent":
            # Just a heuristic: agents should not import sibling agents
            part_name = imp.split(".")[1]
            # If importing exact sibling is bad, but usually they might import 'agents.xyz'
            # Let's be strict: Vertical modules should only import base_agent from agents.
            if imp not in ALLOWED_PREFIXES:
                violations.append(f"Illegal import: {imp}")
        
        if imp.startswith("environments.") and imp != "environments.base_env":
            if imp not in ALLOWED_PREFIXES:
                violations.append(f"Illegal import: {imp}")
                
    if violations:
        for v in violations:
            print(f"  [FAIL] {v}")
        return False
    else:
        print("  [PASS] Dependencies clean.")
        return True

def main():
    target_files = [
        "agents/finance_agent.py",
        "environments/robotics_sim.py"
    ]
    
    overall_pass = True
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for relative_path in target_files:
        full_path = os.path.join(base_dir, relative_path)
        if os.path.exists(full_path):
            if not check_file(full_path):
                overall_pass = False
        else:
            print(f"Warning: File not found {full_path}")
            
    if not overall_pass:
        sys.exit(1)
    else:
        print("\nAll vertical modules passed dependency check.")

if __name__ == "__main__":
    main()
