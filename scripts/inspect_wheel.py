import zipfile
import sys
import os

def inspect_wheel(wheel_path):
    print(f"Inspecting wheel: {wheel_path}")
    forbidden_prefixes = ["tests/", "golden/", "data/", ".env", "temp_"]
    
    try:
        with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(f"Total files: {len(file_list)}")
            
            issues = []
            for file in file_list:
                # Check for forbidden files
                for prefix in forbidden_prefixes:
                    if file.startswith(prefix) or f"/{prefix}" in file:
                         issues.append(f"Forbidden file found: {file}")
                
                # Check for unexpected top-level files (should only be agent_forge/ or agent_forge-0.2.0.dist-info/)
                parts = file.split('/')
                if len(parts) > 0:
                    top_level = parts[0]
                    if top_level not in ["agent_forge", "agent_forge-0.2.0.dist-info"]:
                         # It is common to have .data directory but let's flag anything else
                        issues.append(f"Unexpected top-level file/dir: {file}")

            # Check entry points
            if "agent_forge-0.2.0.dist-info/entry_points.txt" in file_list:
                print("Entry points file found.")
                with zip_ref.open("agent_forge-0.2.0.dist-info/entry_points.txt") as f:
                    content = f.read().decode('utf-8')
                    print("Entry Points Content:")
                    print(content)
                    if "agent-forge = agent_forge.cli:app" not in content and "agent-forge=agent_forge.cli:app" not in content:
                         issues.append("Missing or incorrect 'agent-forge' entry point")
            else:
                issues.append("entry_points.txt missing in dist-info")

            if issues:
                print("\nFAILED: Issues found:")
                for i in issues:
                    print(f"- {i}")
                sys.exit(1)
            else:
                print("\nPASS: Wheel verification successful. No forbidden files found.")
                
    except Exception as e:
        print(f"Error inspecting wheel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_wheel.py <path_to_wheel>")
        sys.exit(1)
    
    inspect_wheel(sys.argv[1])
