
import sys
import sqlite3
import csv
import json
from datetime import datetime

METRICS_FILE = "logs/learning_metrics.csv"
MEMORY_DB = "data/memory.db"
EVENTS_LOG = "logs/simulation_events.jsonl"

def trace_agent(agent_id, time_window_seconds=10):
    print(f"--- TRACING AGENT: {agent_id} ---")
    
    # 1. Load Errors/Events
    errors = []
    try:
        with open(EVENTS_LOG, "r") as f:
            for line in f:
                try:
                    evt = json.loads(line)
                    if agent_id in evt.get("msg", ""):
                        errors.append(evt)
                except: pass
    except: pass
    
    print(f"Found {len(errors)} error events.")
    
    # 2. Load Action/Reward History (Metrics)
    actions = []
    try:
         with open(METRICS_FILE, "r") as f:
            reader = csv.reader(f)
            header = next(reader) # timestamp, step, agent_id, epsilon, reward
            for row in reader:
                if len(row) > 2 and row[2] == agent_id:
                    actions.append({
                        "timestamp": row[0],
                        "step": row[1],
                        "epsilon": row[3],
                        "reward": row[4]
                    })
    except: pass
    
    print(f"Found {len(actions)} action steps.")
    
    # 3. Load Memory (State/Messages)
    memories = []
    try:
        conn = sqlite3.connect(MEMORY_DB)
        c = conn.cursor()
        c.execute("SELECT timestamp, type, content FROM memories WHERE agent_id=? ORDER BY timestamp", (agent_id,))
        rows = c.fetchall()
        for r in rows:
            memories.append({
                "timestamp": r[0],
                "type": r[1],
                "content": r[2]
            })
        conn.close()
    except: pass
    print(f"Found {len(memories)} memory records.")

    # 4. Reconstruct Timeline
    timeline = []
    
    # Add Actions
    for a in actions:
        timeline.append({"ts": a["timestamp"], "type": "ACTION", "data": a})
        
    # Add Memories
    for m in memories:
        timeline.append({"ts": m["timestamp"], "type": f"MEMORY_{m['type'].upper()}", "data": m["content"]})
        
    # Add Errors
    for e in errors:
        timeline.append({"ts": e["timestamp"], "type": "ERROR", "data": e["msg"]})
        
    # Sort
    timeline.sort(key=lambda x: x["ts"])
    
    # Display last N events
    print("\n--- TIMELINE (Last 10 events) ---")
    for event in timeline[-20:]:
        print(f"[{event['ts']}] {event['type']}: {event['data']}")
        
    if not timeline:
        print("No events found. Agent might be idle or logs missing.")

    # 5. Narrative Reconstruction for last error
    if errors:
        last_error = errors[-1]
        err_ts = last_error["timestamp"]
        print(f"\n--- AUDIT FOR ERROR AT {err_ts} ---")
        
        # Find context before error
        context_events = [e for e in timeline if e["ts"] <= err_ts][-5:]
        
        print("Context:")
        for e in context_events:
            print(f"  {e['type']} -> {e['data']}")
            
        print("\nReconstruction:")
        print("1. What the agent knew: (Inferred from last memory/action)")
        print("2. Why it chose action: (Check epsilon in last action)")
        print("3. Feedback: (Check reward/error)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        trace_agent(sys.argv[1])
    else:
        # Default hunt for an agent with errors
        trace_agent("Agent-1")
