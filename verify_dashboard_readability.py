import json
import sys

def verify_readability():
    print("Verifying Dashboard Readability...")
    
    try:
        with open("dashboard_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("FAIL: dashboard_data.json not found. Run generate_risk_story.py first.")
        sys.exit(1)
        
    print(f"Loaded {len(data)} events.\n")
    
    # Narrative Analysis
    story_elements = {
        "DECISION": False,
        "MARKET": False,
        "FAILURE": False,
        "EXPLANATION": False
    }
    
    print("--- Narrative Check ---")
    for event in data:
        t = event['type']
        d = event['details']
        
        if t == "DECISION":
            story_elements["DECISION"] = True
            # Verify details are specific
            if "$" not in d and "@" not in d:
                print(f"WARNING: Decision details vague: {d}")
                
        if t == "MARKET":
            story_elements["MARKET"] = True
            
        if t == "CRITICAL_FAILURE":
            story_elements["FAILURE"] = True
            # Verify explanation clarity
            if "Drawdown" in d and "%" in d:
                story_elements["EXPLANATION"] = True
                
        print(f"[{t}] {d}")

    print("\n--- Verification Results ---")
    missing = [k for k, v in story_elements.items() if not v]
    
    if missing:
        print(f"FAIL: Story is incomplete. Missing: {missing}")
        sys.exit(1)
        
    print("SUCCESS: The dashboard tells a complete story:")
    print("1. Cause (Decision) -> Identified")
    print("2. Condition (Market) -> Identified")
    print("3. Effect (Failure) -> Identified")
    print("4. Reason (Explanation) -> Clear numbers provided.")

if __name__ == "__main__":
    verify_readability()
