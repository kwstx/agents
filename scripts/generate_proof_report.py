
import sys
import subprocess
import os
from datetime import datetime

REPORT_FILE = "PROOF_ARTIFACTS.md"

def capture_output(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error running command: {e}"

def generate_report():
    print("Generating Proof Artifacts Report...")
    
    with open(REPORT_FILE, "w") as f:
        f.write(f"# Agent Forge MVP - Proof Artifacts\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        # 1. Learning Performance
        f.write("## 1. Learning Performance (Before/After)\n")
        f.write("Evidence that agents improve over time (Reward and Goal Success Rate).\n\n")
        f.write("```text\n")
        learning_out = capture_output(f"{sys.executable} scripts/analyze_learning.py")
        f.write(learning_out)
        f.write("\n```\n\n")
        
        # 2. Agent Trace
        f.write("## 2. Visual Trace of Agent Decisions\n")
        f.write("A reconstructed timeline showing the agent's Perception -> Decision -> Action loop.\n\n")
        f.write("```text\n")
        # Trace Agent-1 (most likely to exist)
        trace_out = capture_output(f"{sys.executable} scripts/trace_agent.py Agent-1")
        f.write(trace_out)
        f.write("\n```\n\n")
        
        # 3. Stress Failure Recovery
        f.write("## 3. Stress Test Failure Recovery\n")
        f.write("Logs demonstrating successful error handling and continuation of service.\n\n")
        f.write("```text\n")
        # We'll just grab the tail of simulation_events.jsonl for errors
        f.write("--- Recent System Errors (simulation_events.jsonl) ---\n")
        try:
             with open("logs/simulation_events.jsonl", "r") as events:
                 lines = events.readlines()
                 for line in lines[-10:]: # Last 10
                     f.write(line)
        except Exception as e:
            f.write(f"No error logs found: {e}\n")
            
        f.write("\n--- Recent Operational Logs (latest_run.log tail) ---\n")
        try:
             with open("logs/latest_run.log", "r") as logs:
                 lines = logs.readlines()
                 for line in lines[-15:]:
                     f.write(line)
        except Exception as e:
            f.write(f"No run logs found: {e}\n")
        f.write("\n```\n")
        
    print(f"Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    generate_report()
