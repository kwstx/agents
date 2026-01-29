import os
import json
import glob
import pandas as pd

# Paths
CONTROL_FILE = "control.json"
METRICS_FILE = "logs/learning_metrics.csv"
EVENT_LOG = "logs/simulation_events.jsonl"
LOG_DIR = "logs/checkpoints"
MESSAGE_LOG = "logs/message_bus.jsonl"

def load_control():
    try:
        if os.path.exists(CONTROL_FILE):
            with open(CONTROL_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"status": "STOPPED", "stress_config": {}, "agent_params": {}}

def save_control(config):
    with open(CONTROL_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_metrics():
    if os.path.exists(METRICS_FILE):
        try:
            df = pd.read_csv(METRICS_FILE)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame()

def load_events():
    events = []
    if os.path.exists(EVENT_LOG):
        with open(EVENT_LOG, "r") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except:
                    pass
    return events

def get_available_agents():
    if not os.path.exists(LOG_DIR):
        return []
    return [d for d in os.listdir(LOG_DIR) if os.path.isdir(os.path.join(LOG_DIR, d))]

def get_agent_checkpoints(agent_id):
    agent_dir = os.path.join(LOG_DIR, agent_id)
    if not os.path.exists(agent_dir):
        return []
    files = glob.glob(os.path.join(agent_dir, "*.json"))
    files.sort(reverse=True)
    return files

def load_checkpoint(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def load_messages():
    data = []
    if os.path.exists(MESSAGE_LOG):
        with open(MESSAGE_LOG, "r") as f:
            for line in f:
                try: data.append(json.loads(line))
                except: continue
    return data
