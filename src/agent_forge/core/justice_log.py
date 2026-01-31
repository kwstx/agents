"""
Hash-Chained Justice Log
Immutable, tamper-proof logging system for forensic evidence
"""

import hashlib
import json
import time
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """Single entry in the Justice Log"""
    entry_id: str
    timestamp: float
    previous_hash: str
    data: Dict[str, Any]
    signature: str  # Hash of this entry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(**d)


class JusticeLogger:
    """
    Hash-chained immutable logger for forensic evidence.
    Each entry references the hash of the previous entry, making tampering detectable.
    """
    
    def __init__(self, log_path: str = "justice_log.jsonl"):
        self.log_path = log_path
        self.chain: List[LogEntry] = []
        self.last_hash = "GENESIS"  # Genesis block
        
        # Load existing chain if present
        if os.path.exists(log_path):
            self._load_chain()
    
    def _compute_hash(self, entry_id: str, timestamp: float, previous_hash: str, data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of entry"""
        content = f"{entry_id}|{timestamp}|{previous_hash}|{json.dumps(data, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def log(self, event_type: str, agent_id: str, data: Dict[str, Any]) -> LogEntry:
        """
        Add a new entry to the Justice Log.
        Returns the created entry.
        """
        entry_id = f"{event_type}_{int(time.time() * 1000000)}"
        timestamp = time.time()
        
        # Compute signature
        signature = self._compute_hash(entry_id, timestamp, self.last_hash, data)
        
        # Create entry
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            previous_hash=self.last_hash,
            data=data,
            signature=signature
        )
        
        # Append to chain
        self.chain.append(entry)
        self.last_hash = signature
        
        # Write to disk (append-only)
        self._append_to_disk(entry)
        
        return entry
    
    def _append_to_disk(self, entry: LogEntry):
        """Append entry to disk in JSONL format"""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')
    
    def _load_chain(self):
        """Load existing chain from disk"""
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    entry_dict = json.loads(line)
                    entry = LogEntry.from_dict(entry_dict)
                    self.chain.append(entry)
                    self.last_hash = entry.signature
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire chain.
        Returns a dict with verification results.
        """
        if not self.chain:
            return {
                "valid": True,
                "total_entries": 0,
                "message": "Empty chain (valid)"
            }
        
        expected_previous = "GENESIS"
        
        for idx, entry in enumerate(self.chain):
            # Check previous hash linkage
            if entry.previous_hash != expected_previous:
                return {
                    "valid": False,
                    "total_entries": len(self.chain),
                    "failed_at_index": idx,
                    "failed_entry_id": entry.entry_id,
                    "message": f"Hash chain broken at entry {idx}. Expected previous_hash={expected_previous}, got={entry.previous_hash}"
                }
            
            # Recompute signature
            computed_sig = self._compute_hash(
                entry.entry_id,
                entry.timestamp,
                entry.previous_hash,
                entry.data
            )
            
            if computed_sig != entry.signature:
                return {
                    "valid": False,
                    "total_entries": len(self.chain),
                    "failed_at_index": idx,
                    "failed_entry_id": entry.entry_id,
                    "message": f"Signature mismatch at entry {idx}. Entry has been tampered with."
                }
            
            expected_previous = entry.signature
        
        return {
            "valid": True,
            "total_entries": len(self.chain),
            "first_entry": self.chain[0].entry_id if self.chain else None,
            "last_entry": self.chain[-1].entry_id if self.chain else None,
            "message": "All entries verified. Chain is intact."
        }
    
    def seal(self) -> Dict[str, Any]:
        """
        Generate a tamper-proof manifest of the entire log.
        Returns manifest with hashes and metadata.
        """
        if not self.chain:
            return {
                "sealed_at": time.time(),
                "total_entries": 0,
                "chain_hash": "EMPTY",
                "message": "No entries to seal"
            }
        
        # Compute hash of entire chain
        chain_content = "".join([entry.signature for entry in self.chain])
        chain_hash = hashlib.sha256(chain_content.encode()).hexdigest()
        
        manifest = {
            "sealed_at": time.time(),
            "sealed_at_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "total_entries": len(self.chain),
            "first_entry_id": self.chain[0].entry_id,
            "first_timestamp": self.chain[0].timestamp,
            "last_entry_id": self.chain[-1].entry_id,
            "last_timestamp": self.chain[-1].timestamp,
            "chain_hash": chain_hash,
            "log_file": self.log_path
        }
        
        # Write manifest to disk
        manifest_path = self.log_path.replace('.jsonl', '_manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def get_entries(self, limit: Optional[int] = None, offset: int = 0) -> List[LogEntry]:
        """Get entries from the chain with pagination"""
        if limit is None:
            return self.chain[offset:]
        return self.chain[offset:offset+limit]
    
    def get_entry_by_id(self, entry_id: str) -> Optional[LogEntry]:
        """Find entry by ID"""
        for entry in self.chain:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def export_audit_trail(self, output_path: str):
        """Export human-readable audit trail"""
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(" ENGRAM JUSTICE LOG - AUDIT TRAIL\n")
            f.write(f" Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(" Security Rank: OFFICIAL / AUDIT-READY\n")
            f.write("=" * 80 + "\n\n")
            
            for idx, entry in enumerate(self.chain):
                f.write(f"[Entry {idx+1}] {entry.entry_id}\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry.timestamp))}\n")
                f.write(f"Previous Hash: {entry.previous_hash[:16]}...\n")
                f.write(f"Signature: {entry.signature[:16]}...\n")
                f.write(f"Data: {json.dumps(entry.data, indent=2)}\n")
                f.write("-" * 80 + "\n\n")
            
            # Add verification
            verification = self.verify_integrity()
            f.write("=" * 80 + "\n")
            f.write(" VERIFICATION RESULTS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Valid: {verification['valid']}\n")
            f.write(f"Total Entries: {verification['total_entries']}\n")
            f.write(f"Message: {verification['message']}\n")
            f.write("=" * 80 + "\n")


# Global singleton instance
_justice_logger: Optional[JusticeLogger] = None


def get_justice_logger(log_path: str = "justice_log.jsonl") -> JusticeLogger:
    """Get or create the global Justice Logger instance"""
    global _justice_logger
    if _justice_logger is None:
        _justice_logger = JusticeLogger(log_path)
    return _justice_logger
