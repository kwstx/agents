import os
import json
import filecmp
import sys
import glob

def compare_json_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        j1 = json.load(f1)
        j2 = json.load(f2)
    
    if j1 == j2:
        return True, ""
    else:
        return False, "JSON content differs"

def main():
    golden_root = "golden"
    if not os.path.exists(golden_root):
        print("Golden root not found")
        sys.exit(1)
        
    dirs = sorted([d for d in os.listdir(golden_root) if os.path.isdir(os.path.join(golden_root, d))])
    
    if len(dirs) < 2:
        print("Not enough golden runs to compare.")
        sys.exit(1)
        
    baseline_dir = os.path.join(golden_root, dirs[-2]) 
    new_dir = os.path.join(golden_root, dirs[-1])     
    
    print(f"Comparing Baseline: {baseline_dir}")
    print(f"       Vs New Run: {new_dir}")
    
    scenarios = ["single_agent_grid", "multi_agent_finance", "stress_test", "failure_case"]
    
    overall_pass = True
    
    for sc in scenarios:
        print(f"\n--- Checking Scenario: {sc} ---")
        base_path = os.path.join(baseline_dir, sc)
        new_path = os.path.join(new_dir, sc)
        
        if not os.path.exists(base_path):
            print(f"WARNING: Baseline missing scenario {sc}")
            continue
            
        f1 = os.path.join(base_path, "final_state.json")
        f2 = os.path.join(new_path, "final_state.json")
        
        if os.path.exists(f1) and os.path.exists(f2):
            match, msg = compare_json_files(f1, f2)
            if match:
                print("  [PASS] final_state.json matches")
            else:
                print(f"  [FAIL] final_state.json DIFFERS")
                # Debug diff
                with open(f1) as a, open(f2) as b:
                     print(f"   Base: {a.read()[:100]}...")
                     print(f"   New : {b.read()[:100]}...")
                overall_pass = False
        else:
             print("  [WARN] missing final_state.json")

        l1 = os.path.join(base_path, "events.jsonl")
        l2 = os.path.join(new_path, "events.jsonl")
        
        if os.path.exists(l1) and os.path.exists(l2):
             with open(l1, 'r') as log1, open(l2, 'r') as log2:
                 lines1 = log1.readlines()
                 lines2 = log2.readlines()
                 
                 if len(lines1) != len(lines2):
                      print(f"  [FAIL] events.jsonl length differs: {len(lines1)} vs {len(lines2)}")
                      overall_pass = False
                      continue

                 metrics_match = True
                 for i, (a, b) in enumerate(zip(lines1, lines2)):
                     try:
                         j1 = json.loads(a)
                         j2 = json.loads(b)
                         
                         j1.pop("timestamp", None)
                         j2.pop("timestamp", None)
                         
                         # Action IDs often have random suffix in some scenarios (multi-agent) unless perfectly seeded
                         # Let's see if we need to accept that.
                         # If strictly seeded, they should match.
                         
                         if j1 != j2:
                             print(f"    Line {i} mismatch:")
                             print(f"    Base: {j1}")
                             print(f"    New : {j2}")
                             metrics_match = False
                             break
                     except json.JSONDecodeError:
                         if a != b:
                             print(f"    Line {i} raw mismatch (not JSON):")
                             metrics_match = False
                             break
                
                 if metrics_match:
                     print("  [PASS] events.jsonl matches (semantically)")
                 else:
                     overall_pass = False

    if overall_pass:
        print("\nSUCCESS: All golden artifacts match.")
        sys.exit(0)
    else:
        print("\nFAILURE: Golden artifacts diverged.")
        sys.exit(1)

if __name__ == "__main__":
    main()
