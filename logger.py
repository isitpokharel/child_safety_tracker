"""
Audit Logger Module
Author: Pooja Poudel
Purpose: Log and track system events and statistics
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """Log entry data structure."""
    timestamp: str
    event_type: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Thread-safe audit logger with statistics tracking."""
    
    def __init__(self, log_file: str = "audit.log"):
        """Initialize logger with log file path."""
        self.log_file = log_file
        self._entries: List[LogEntry] = []
        self._stats: Dict[str, int] = {
            "total_entries": 0,
            "location_updates": 0,
            "panic_events": 0,
            "geofence_violations": 0,
            "errors": 0
        }
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
    
    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an event with type and details."""
        if not event_type:
            raise ValueError("Event type cannot be empty")
        if not isinstance(details, dict):
            raise ValueError("Details must be a dictionary")
        
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            details=details
        )
        
        with self._lock:
            self._entries.append(entry)
            self._stats["total_entries"] += 1
            
            # Update specific counters
            if event_type == "location_update":
                self._stats["location_updates"] += 1
            elif event_type == "panic":
                self._stats["panic_events"] += 1
            elif event_type == "geofence_violation":
                self._stats["geofence_violations"] += 1
            elif event_type == "error":
                self._stats["errors"] += 1
        
        # Write to file
        with self._file_lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(entry.to_json() + "\n")
            except Exception as e:
                print(f"Error writing to log file: {e}")
    
    def get_recent_entries(self, count: int = 10) -> List[LogEntry]:
        """Get most recent log entries."""
        with self._lock:
            return self._entries[-count:]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get current statistics."""
        with self._lock:
            return self._stats.copy()
    
    def clear(self) -> None:
        """Clear all entries and reset statistics."""
        with self._lock:
            self._entries.clear()
            self._stats = {
                "total_entries": 0,
                "location_updates": 0,
                "panic_events": 0,
                "geofence_violations": 0,
                "errors": 0
            }
        
        # Clear log file
        with self._file_lock:
            try:
                with open(self.log_file, "w") as f:
                    f.write("")
            except Exception as e:
                print(f"Error clearing log file: {e}")


# Convenience functions
def create_logger(log_file: Optional[str] = None) -> AuditLogger:
    """Create a new audit logger instance."""
    if log_file is None:
        log_file = f"audit_{int(time.time())}.log"
    return AuditLogger(log_file) 