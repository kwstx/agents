
import sys
import os

LOG_FILE = "logs/simulation_events.jsonl" 
# Agents log to standard logger (SimulationRunner). 
# We should inspect the console output or if we have a log file for general logs.
# SimulationRunner uses basic config logger, which goes to stderr/stdout usually.
# However, agents usually have their own loggers. 
# In `simulation_runner.py`: logging.basicConfig(level=logging.INFO)
# This goes to stderr by default.

# For this test to work reliably, we need to capture the runner output in run_scenario or logging to file.
# Since run_scenario prints, but we didn't redirect to file.

# Let's check `data/memory.db`. Collaborative agents should log to memory?
# BaseAgent.log_activity logs to memory.
# CollaborativeAgent calls self.logger.info, which hits BaseAgent.logger.
# But it does NOT call log_activity for "Visiting..." unless we added it.
# Check CollaborativeExplorerAgent implementation:
# It calls self.logger.info(...)
# It calls self.send_message(...) which calls log_activity("message_sent", ...)
# It calls on_step_complete -> send_message.

# So we can check memory.db for "message_sent" with topic "exploration_update".

import sqlite3
import json

DB_PATH = "data/memory.db"

def verify_collaboration():
    if not os.path.exists(DB_PATH):
        print(f"FAIL: {DB_PATH} not found.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query for exploration_update messages
    cursor.execute("SELECT content FROM memories WHERE type='message_sent'")
    rows = cursor.fetchall()
    
    updates = 0
    for row in rows:
        try:
            content = json.loads(row[0])
            if content.get("topic") == "exploration_update":
                updates += 1
        except:
            pass
            
    print(f"Found {updates} exploration_update messages in memory.")
    
    if updates > 0:
        print("SUCCESS: Agents are sharing exploration state.")
    else:
        print("FAIL: No exploration updates found.")
        sys.exit(1)
        
    conn.close()

if __name__ == "__main__":
    verify_collaboration()
