import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("Memory")

class Memory:
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self._ensure_dir()
        
        # Connect to DB. check_same_thread=False is needed if multiple threads share the connection,
        # but robust apps often use a connection per thread or pool. For this MVP, we'll be careful
        # or rely on individual agents creating their own Memory instance (which points to same DB file).
        # Since BaseAgent creates its own Memory instance, we are safe with check_same_thread=True usually,
        # UNLESS we share the memory object across threads. 
        # Multi-process (agents is separate processes) is fine with SQLite.
        self.conn = sqlite3.connect(self.db_path) 
        
        # Enable WAL (Write-Ahead Logging) for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        self._init_schema()

    def _ensure_dir(self):
        dirname = os.path.dirname(self.db_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

    def _init_schema(self):
        query = """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            sim_context TEXT
        );
        """
        with self.conn:
            self.conn.execute(query)
            # Index for faster frequent lookups
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_timestamp ON memories(agent_id, timestamp);")

    def add_memory(self, agent_id: str, type: str, content: Any, sim_context: Optional[Dict] = None):
        """
        Adds a new memory entry.
        content and sim_context are serialized to JSON.
        """
        if not isinstance(content, str):
            content_json = json.dumps(content)
        else:
            content_json = content
            
        sim_context_json = json.dumps(sim_context) if sim_context else None
        timestamp = datetime.now().isoformat()

        query = """
        INSERT INTO memories (agent_id, type, content, timestamp, sim_context)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.conn:
                self.conn.execute(query, (agent_id, type, content_json, timestamp, sim_context_json))
        except sqlite3.OperationalError as e:
            logger.error(f"DB Write failed: {e}")
            raise

    def query_memory(self, agent_id: str = None, type: str = None, 
                     start_time: str = None, end_time: str = None, 
                     filter_metadata: Dict[str, Any] = None,
                     limit: int = 50) -> List[Dict]:
        """
        Query memories with advanced filters.
        Time range should be ISO format strings.
        filter_metadata checks if key-value pairs exist in sim_context.
        """
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if type:
            query += " AND type = ?"
            params.append(type)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC, id DESC"
        
        # If we have basic DB filters, we fetch more than limit because we might filter out 
        # items in Python based on metadata, so applied limit at the very end.
        # But for performance on huge datasets, we should ideally use SQL JSON. 
        # For this MVP, we will fetch up to limit * 10 candidates if metadata filter is on, 
        # or just fetch all logic if needed. 
        # Let's apply limit only if no metadata filter, OR apply limit at the end of python processing.
        # For safety/performance trade-off: apply SQL limit only if NO metadata filter.
        
        if not filter_metadata:
             query += " LIMIT ?"
             params.append(limit)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            # row: id, agent_id, type, content, timestamp, sim_context
            try:
                sim_context = json.loads(row[5]) if row[5] else None
            except json.JSONDecodeError:
                sim_context = row[5]

            # Metadata Filter (Python side)
            if filter_metadata:
                if not isinstance(sim_context, dict):
                    continue
                match = True
                for k, v in filter_metadata.items():
                    if sim_context.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            try:
                content = json.loads(row[3])
            except json.JSONDecodeError:
                content = row[3]

            results.append({
                "id": row[0],
                "agent_id": row[1],
                "type": row[2],
                "content": content,
                "timestamp": row[4],
                "sim_context": sim_context
            })
            
            if len(results) >= limit:
                break
        
        return results

    def get_recent(self, agent_id: str, limit: int = 10) -> List[Dict]:
        return self.query_memory(agent_id=agent_id, limit=limit)

    def summarize_context(self, agent_id: str, limit: int = 100) -> List[str]:
        """
        Retrieves recent memories and performs heuristic condensation.
        Useful for feeding LLMs without context window overflow.
        Strategy:
        1. Retrieve last N items.
        2. Collapse consecutive duplicate actions (e.g. "Moved North" x5).
        3. Return list of formatted strings.
        """
        raw_memories = self.get_recent(agent_id, limit)
        # Sort by timestamp ascending for the summary (chronological)
        raw_memories.reverse()
        
        summary = []
        if not raw_memories:
            return summary
            
        last_content = None
        count = 0
        
        for mem in raw_memories:
            content_str = str(mem["content"])
            
            if content_str == last_content:
                count += 1
            else:
                if last_content:
                    if count > 1:
                        summary.append(f"{last_content} (x{count})")
                    else:
                        summary.append(last_content)
                
                last_content = content_str
                count = 1
        
        # Flush last
        if last_content:
            if count > 1:
                summary.append(f"{last_content} (x{count})")
            else:
                summary.append(last_content)
                
        return summary

    def close(self):
        self.conn.close()
