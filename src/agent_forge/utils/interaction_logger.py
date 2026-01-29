import sqlite3
import json
import time
import os
from typing import Any, Dict

class InteractionLogger:
    def __init__(self, db_path: str = "simulation_logs.db", log_file: str = "simulation_events.jsonl"):
        self.db_path = db_path
        self.log_file = log_file
        self._setup_db()
        self._setup_json_log()

    def _setup_db(self):
        """Initialize the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent_id TEXT,
                action TEXT,
                state TEXT,
                state_hash TEXT,
                reward REAL,
                metadata TEXT
            )
        ''')
        # Check if state_hash column exists (migration for existing db)
        cursor.execute("PRAGMA table_info(interactions)")
        columns = [info[1] for info in cursor.fetchall()]
        if "state_hash" not in columns:
            cursor.execute("ALTER TABLE interactions ADD COLUMN state_hash TEXT")
            
        conn.commit()
        conn.close()

    def _setup_json_log(self):
        """Ensure the JSON log file exists or is cleared/ready."""
        # For this MVP, we just ensure the directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log_interaction(self, agent_id: str, action: str, state: Any, reward: float, metadata: Dict[str, Any] = None, state_hash: str = None):
        """Log an interaction to both SQLite and JSONL."""
        timestamp = time.time()
        metadata_json = json.dumps(metadata) if metadata else "{}"
        state_str = str(state) # Convert complex states to string for DB

        # 1. SQLite Logging
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO interactions (timestamp, agent_id, action, state, state_hash, reward, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, agent_id, action, state_str, state_hash, reward, metadata_json))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging to SQLite: {e}")

        # 2. JSONL Logging
        try:
            log_entry = {
                "timestamp": timestamp,
                "agent_id": agent_id,
                "action": action,
                "state": state,
                "state_hash": state_hash,
                "reward": reward,
                "metadata": metadata
            }
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging to JSONL: {e}")

    def get_logs(self, agent_id: str = None, limit: int = 100):
        """Retrieve logs from SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if agent_id:
            cursor.execute('SELECT * FROM interactions WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?', (agent_id, limit))
        else:
            cursor.execute('SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
