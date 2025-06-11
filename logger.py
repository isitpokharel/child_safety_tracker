"""
Logger Module - Structured JSONL audit writer
Author: Pooja Poudel
Purpose: Audit logging for all system events and location data
"""

import json
import os
from typing import Dict, List, Any, Optional, Deque
from datetime import datetime
from pathlib import Path
import threading
from collections import deque
import gzip
from geofence import Location, Geofence


class AuditLogger:
    """Structured JSONL audit logger for KiddoTrack-Lite with optimizations."""
    
    def __init__(self, log_file_path: str, buffer_size: int = 100, max_file_size: int = 10 * 1024 * 1024):
        """
        Initialize the audit logger.
        
        Args:
            log_file_path: Path to the JSONL log file
            buffer_size: Number of entries to buffer before writing
            max_file_size: Maximum file size in bytes before rotation
        """
        self.log_file_path = Path(log_file_path)
        self._lock = threading.Lock()
        self.buffer_size = buffer_size
        self.max_file_size = max_file_size
        
        # Internal buffer for batching writes
        self._buffer: Deque[Dict[str, Any]] = deque()
        self._buffer_lock = threading.Lock()
        
        # Cache for recent entries to avoid frequent file reads
        self._recent_cache: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self._cache_lock = threading.Lock()
        
        # Ensure directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file if it doesn't exist
        if not self.log_file_path.exists():
            self.log_file_path.touch()
        
        # Load recent entries into cache
        self._load_recent_cache()
    
    def _load_recent_cache(self):
        """Load recent entries into cache for faster access."""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                # Read last 1000 lines efficiently
                lines = deque(f, maxlen=1000)
                
            with self._cache_lock:
                self._recent_cache.clear()
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self._recent_cache.append(entry)
                        except json.JSONDecodeError:
                            continue
                            
        except (FileNotFoundError, IOError):
            pass
    
    def _should_rotate_log(self) -> bool:
        """Check if log file should be rotated."""
        try:
            return self.log_file_path.stat().st_size > self.max_file_size
        except OSError:
            return False
    
    def _rotate_log(self):
        """Rotate log file by compressing and archiving."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = self.log_file_path.with_suffix(f'.{timestamp}.gz')
            
            # Compress current log file
            with open(self.log_file_path, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Clear current log file
            self.log_file_path.write_text('')
            print(f"Log rotated to {archive_path}")
            
        except Exception as e:
            print(f"Error rotating log: {e}")
    
    def _flush_buffer(self):
        """Flush the internal buffer to file."""
        if not self._buffer:
            return
            
        with self._buffer_lock:
            entries_to_write = list(self._buffer)
            self._buffer.clear()
        
        if not entries_to_write:
            return
            
        try:
            # Check if rotation is needed
            if self._should_rotate_log():
                self._rotate_log()
            
            # Write all buffered entries at once
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                for entry in entries_to_write:
                    json.dump(entry, f, ensure_ascii=False)
                    f.write('\n')
                f.flush()
            
            # Update cache
            with self._cache_lock:
                self._recent_cache.extend(entries_to_write)
                
        except Exception as e:
            print(f"Error writing to audit log: {e}")
    
    def _write_log_entry(self, entry: Dict[str, Any]):
        """
        Buffer a log entry for writing.
        
        Args:
            entry: Dictionary containing log data
        """
        with self._buffer_lock:
            self._buffer.append(entry)
            should_flush = len(self._buffer) >= self.buffer_size
        
        if should_flush:
            with self._lock:
                self._flush_buffer()
    
    def _create_base_entry(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """
        Create a base log entry with common fields.
        
        Args:
            event_type: Type of event being logged
            **kwargs: Additional fields to include
            
        Returns:
            Dictionary with base log entry structure
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **kwargs
        }
        return entry
    
    def log_location(self, location: Location):
        """
        Log a location update.
        
        Args:
            location: Location object to log
        """
        entry = self._create_base_entry(
            "location_update",
            latitude=location.latitude,
            longitude=location.longitude,
            timestamp=location.timestamp or datetime.now().isoformat()
        )
        self._write_log_entry(entry)
    
    def log_alert(self, alert_data: Dict[str, Any]):
        """
        Log an alert event.
        
        Args:
            alert_data: Alert data dictionary
        """
        entry = self._create_base_entry(
            "alert",
            **alert_data
        )
        self._write_log_entry(entry)
    
    def log_geofence_update(self, geofence_data: Dict[str, Any]):
        """
        Log a geofence configuration update.
        
        Args:
            geofence_data: Geofence configuration data
        """
        entry = self._create_base_entry(
            "geofence_update",
            **geofence_data
        )
        self._write_log_entry(entry)
    
    def log_panic_trigger(self):
        """Log a panic trigger event."""
        entry = self._create_base_entry(
            "panic_trigger",
            severity="critical"
        )
        self._write_log_entry(entry)
    
    def log_panic_resolution(self):
        """Log a panic resolution event."""
        entry = self._create_base_entry(
            "panic_resolution",
            severity="medium"
        )
        self._write_log_entry(entry)
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """
        Log a system event.
        
        Args:
            event: Event description
            details: Optional additional details
        """
        entry = self._create_base_entry(
            "system_event",
            event=event,
            details=details or {}
        )
        self._write_log_entry(entry)
    
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """
        Log an error event.
        
        Args:
            error: Error message
            context: Optional context information
        """
        entry = self._create_base_entry(
            "error",
            error_message=error,
            context=context or {}
        )
        self._write_log_entry(entry)
    
    def get_recent_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent log entries from cache (optimized).
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of recent log entries
        """
        # Ensure any buffered entries are written first
        with self._lock:
            self._flush_buffer()
        
        with self._cache_lock:
            entries = list(self._recent_cache)
        
        # Return last 'limit' entries
        return entries[-limit:] if len(entries) > limit else entries
    
    def force_flush(self):
        """Force flush any buffered entries to disk."""
        with self._lock:
            self._flush_buffer()
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent alert entries (optimized).
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alert entries
        """
        with self._cache_lock:
            all_entries = list(self._recent_cache)
        
        alerts = [entry for entry in all_entries if entry.get('event_type') == 'alert']
        return alerts[-limit:] if len(alerts) > limit else alerts
    
    def get_recent_locations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent location entries (optimized).
        
        Args:
            limit: Maximum number of locations to return
            
        Returns:
            List of recent location entries
        """
        with self._cache_lock:
            all_entries = list(self._recent_cache)
        
        locations = [entry for entry in all_entries if entry.get('event_type') == 'location_update']
        return locations[-limit:] if len(locations) > limit else locations
    
    def get_entries_by_type(self, event_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get entries filtered by event type (optimized).
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of entries to return
            
        Returns:
            List of filtered entries
        """
        with self._cache_lock:
            all_entries = list(self._recent_cache)
        
        filtered = [entry for entry in all_entries if entry.get('event_type') == event_type]
        return filtered[-limit:] if len(filtered) > limit else filtered
    
    def get_entries_by_time_range(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        Get entries within a time range.
        
        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            
        Returns:
            List of entries within the time range
        """
        entries = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            timestamp = entry.get('timestamp', '')
                            
                            if start_time <= timestamp <= end_time:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
                            
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading audit log: {e}")
        
        return entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Dictionary with log statistics
        """
        entries = self.get_recent_entries(10000)  # Get a large sample
        
        stats = {
            "total_entries": len(entries),
            "event_types": {},
            "date_range": {
                "earliest": None,
                "latest": None
            }
        }
        
        if entries:
            timestamps = [entry.get('timestamp', '') for entry in entries if entry.get('timestamp')]
            if timestamps:
                stats["date_range"]["earliest"] = min(timestamps)
                stats["date_range"]["latest"] = max(timestamps)
            
            # Count event types
            for entry in entries:
                event_type = entry.get('event_type', 'unknown')
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
        
        return stats
    
    def clear_log(self):
        """Clear the audit log file."""
        with self._lock:
            try:
                self.log_file_path.unlink(missing_ok=True)
                self.log_file_path.touch()
                print("Audit log cleared")
            except Exception as e:
                print(f"Error clearing audit log: {e}")
    
    def export_log(self, output_path: str, event_types: Optional[List[str]] = None):
        """
        Export log entries to a file.
        
        Args:
            output_path: Path for the exported file
            event_types: Optional list of event types to filter by
        """
        entries = self.get_recent_entries(10000)  # Get a large sample
        
        if event_types:
            entries = [entry for entry in entries if entry.get('event_type') in event_types]
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
            print(f"Log exported to {output_path}")
        except Exception as e:
            print(f"Error exporting log: {e}")


# Convenience functions
def create_audit_logger(log_dir: str = "data") -> AuditLogger:
    """
    Create an audit logger with default settings.
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        AuditLogger instance
    """
    log_path = os.path.join(log_dir, "audit_log.jsonl")
    return AuditLogger(log_path)


def get_logger_statistics(log_file_path: str) -> Dict[str, Any]:
    """
    Get statistics for a specific log file.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Dictionary with log statistics
    """
    logger = AuditLogger(log_file_path)
    return logger.get_statistics() 