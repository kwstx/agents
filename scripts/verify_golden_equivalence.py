import sys
import os
import json
import difflib
from pathlib import Path

def load_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            try:
                obj = json.loads(line)
                # Remove non-deterministic fields
                if 'timestamp' in obj:
                    del obj['timestamp']
                
                # In metadata, there might be timestamps if the system logs them deeper
                # But for now, top-level timestamp is the main one.
                # Recursive strip?
                data.append(obj)
            except json.JSONDecodeError:
                pass
    return data

def load_json(path):
    with open(path, 'r') as f:
        obj = json.load(f)
    return obj

def compare_dirs(golden_dir, candidate_dir):
    print(f"Comparing Golden: {golden_dir}")
    print(f"Against Candidate: {candidate_dir}")
    
    golden_path = Path(golden_dir)
    candidate_path = Path(candidate_dir)
    
    success = True
    
    # 1. Check Directory Structure
    golden_subdirs = sorted([d.name for d in golden_path.iterdir() if d.is_dir()])
    candidate_subdirs = sorted([d.name for d in candidate_path.iterdir() if d.is_dir()])
    
    if golden_subdirs != candidate_subdirs:
        print(f"FAIL: Scenario mismatch.\nGolden: {golden_subdirs}\nCandidate: {candidate_subdirs}")
        return False
        
    for scenario in golden_subdirs:
        print(f"\nChecking Scenario: {scenario}")
        g_scen = golden_path / scenario
        c_scen = candidate_path / scenario
        
        # 1. Compare events.jsonl
        g_events_path = g_scen / "events.jsonl"
        c_events_path = c_scen / "events.jsonl"
        
        if not g_events_path.exists() and not c_events_path.exists():
            print("  events.jsonl: MATCH (Both missing)")
            g_events = []
            c_events = []
        elif g_events_path.exists() != c_events_path.exists():
             print(f"  FAIL: events.jsonl existence mismatch. Golden: {g_events_path.exists()}, Candidate: {c_events_path.exists()}")
             success = False
             continue
        else:
            g_events = load_jsonl(g_events_path)
            c_events = load_jsonl(c_events_path)
        
        if len(g_events) != len(c_events):
            print(f"  FAIL: Event count mismatch. Golden: {len(g_events)}, Candidate: {len(c_events)}")
            success = False
        else:
            mismatch = False
            for i, (g, c) in enumerate(zip(g_events, c_events)):
                # Deep compare
                # Use json.dumps with sort_keys to ignore key order
                g_str = json.dumps(g, sort_keys=True)
                c_str = json.dumps(c, sort_keys=True)
                if g_str != c_str:
                    print(f"  FAIL: Event {i} mismatch.")
                    print(f"    Golden: {g_str}")
                    print(f"    Candidate: {c_str}")
                    mismatch = True
                    success = False
                    break # Stop spamming
            if not mismatch:
                print("  events.jsonl: MATCH")

        # 2. Compare final_state.json
        try:
            g_state = load_json(g_scen / "final_state.json")
            c_state = load_json(c_scen / "final_state.json")
            
            # Remove execution metadata if present?
            # capture_golden_master.py saves pure state mostly.
            
            g_str = json.dumps(g_state, sort_keys=True)
            c_str = json.dumps(c_state, sort_keys=True)
            
            if g_str != c_str:
                print(f"  FAIL: final_state.json mismatch.")
                print(f"    Golden: {g_str}")
                print(f"    Candidate: {c_str}")
                success = False
            else:
                print("  final_state.json: MATCH")
                
        except Exception as e:
            print(f"  FAIL: Error comparing final_state.json: {e}")
            success = False

    return success

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python verify_golden_equivalence.py <golden_dir> <candidate_dir>")
        sys.exit(1)
        
    golden = sys.argv[1]
    candidate = sys.argv[2]
    
    if compare_dirs(golden, candidate):
        print("\nOVERALL: SUCCESS - Behavioral Equivalence Verified.")
        sys.exit(0)
    else:
        print("\nOVERALL: FAILED - Divergence Detected.")
        sys.exit(1)
