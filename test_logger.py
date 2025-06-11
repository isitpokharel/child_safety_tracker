"""
Unit Tests for Logger Module
Author: Pooja Poudel
Purpose: Data-flow testing for structured JSONL audit writer
"""

import pytest
import json
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from logger import AuditLogger, create_audit_logger, get_logger_statistics
from geofence import Location, Geofence


class TestAuditLogger:
    """Test cases for AuditLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "test_audit_log.jsonl")
        self.logger = AuditLogger(self.log_file_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test logger initialization."""
        assert self.logger.log_file_path == Path(self.log_file_path)
        assert self.logger.log_file_path.exists()
        assert self.logger._lock is not None
    
    def test_initialization_creates_directory(self):
        """Test that logger creates directory if it doesn't exist."""
        nested_dir = os.path.join(self.temp_dir, "nested", "deep")
        log_path = os.path.join(nested_dir, "test_log.jsonl")
        
        logger = AuditLogger(log_path)
        
        assert logger.log_file_path.exists()
        assert logger.log_file_path.parent.exists()
    
    def test_write_log_entry(self):
        """Test writing a single log entry."""
        entry = {
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "test",
            "message": "Test entry"
        }
        
        self.logger._write_log_entry(entry)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            written_entry = json.loads(lines[0])
            assert written_entry == entry
    
    def test_create_base_entry(self):
        """Test creating base log entry."""
        entry = self.logger._create_base_entry("test_event", key1="value1", key2="value2")
        
        assert entry["event_type"] == "test_event"
        assert entry["key1"] == "value1"
        assert entry["key2"] == "value2"
        assert "timestamp" in entry
        assert isinstance(entry["timestamp"], str)
    
    def test_log_location(self):
        """Test logging location data."""
        location = Location(40.7128, -74.0060, "2024-01-01T12:00:00")
        
        self.logger.log_location(location)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "location_update"
            assert entry["latitude"] == 40.7128
            assert entry["longitude"] == -74.0060
            assert entry["timestamp"] == "2024-01-01T12:00:00"
    
    def test_log_location_without_timestamp(self):
        """Test logging location without timestamp."""
        location = Location(40.7128, -74.0060)
        
        self.logger.log_location(location)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "location_update"
            assert entry["latitude"] == 40.7128
            assert entry["longitude"] == -74.0060
            assert "timestamp" in entry  # Should have generated timestamp
    
    def test_log_alert(self):
        """Test logging alert data."""
        alert_data = {
            "type": "geofence_exit",
            "message": "Child left safe zone",
            "severity": "high"
        }
        
        self.logger.log_alert(alert_data)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "alert"
            assert entry["type"] == "geofence_exit"
            assert entry["message"] == "Child left safe zone"
            assert entry["severity"] == "high"
    
    def test_log_geofence_update(self):
        """Test logging geofence update."""
        geofence_data = {
            "center": {"latitude": 40.7128, "longitude": -74.0060},
            "radius_meters": 1000.0
        }
        
        self.logger.log_geofence_update(geofence_data)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "geofence_update"
            assert entry["center"]["latitude"] == 40.7128
            assert entry["center"]["longitude"] == -74.0060
            assert entry["radius_meters"] == 1000.0
    
    def test_log_panic_trigger(self):
        """Test logging panic trigger."""
        self.logger.log_panic_trigger()
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "panic_trigger"
            assert entry["severity"] == "critical"
    
    def test_log_panic_resolution(self):
        """Test logging panic resolution."""
        self.logger.log_panic_resolution()
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "panic_resolution"
            assert entry["severity"] == "medium"
    
    def test_log_system_event(self):
        """Test logging system event."""
        details = {"component": "simulator", "action": "started"}
        
        self.logger.log_system_event("Simulator started", details)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "system_event"
            assert entry["event"] == "Simulator started"
            assert entry["details"] == details
    
    def test_log_system_event_no_details(self):
        """Test logging system event without details."""
        self.logger.log_system_event("Simple event")
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "system_event"
            assert entry["event"] == "Simple event"
            assert entry["details"] == {}
    
    def test_log_error(self):
        """Test logging error."""
        context = {"component": "api", "request_id": "12345"}
        
        self.logger.log_error("Connection failed", context)
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "error"
            assert entry["error_message"] == "Connection failed"
            assert entry["context"] == context
    
    def test_log_error_no_context(self):
        """Test logging error without context."""
        self.logger.log_error("Simple error")
        
        # Verify entry was written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "error"
            assert entry["error_message"] == "Simple error"
            assert entry["context"] == {}
    
    def test_multiple_entries(self):
        """Test writing multiple entries."""
        # Write multiple entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_system_event("test event")
        
        # Verify all entries were written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3
            
            # Check each entry
            entry1 = json.loads(lines[0])
            assert entry1["event_type"] == "location_update"
            
            entry2 = json.loads(lines[1])
            assert entry2["event_type"] == "alert"
            
            entry3 = json.loads(lines[2])
            assert entry3["event_type"] == "system_event"
    
    def test_get_recent_entries_empty_file(self):
        """Test getting recent entries from empty file."""
        entries = self.logger.get_recent_entries()
        assert entries == []
    
    def test_get_recent_entries_with_data(self):
        """Test getting recent entries with data."""
        # Write some entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_system_event("test event")
        
        # Get all entries
        entries = self.logger.get_recent_entries()
        assert len(entries) == 3
        
        # Get limited entries
        entries = self.logger.get_recent_entries(limit=2)
        assert len(entries) == 2
    
    def test_get_recent_entries_malformed_lines(self):
        """Test getting recent entries with malformed lines."""
        # Write valid and invalid entries
        with open(self.log_file_path, 'w') as f:
            f.write('{"event_type": "valid", "message": "test"}\n')
            f.write('invalid json line\n')
            f.write('{"event_type": "also_valid", "message": "test2"}\n')
        
        entries = self.logger.get_recent_entries()
        assert len(entries) == 2  # Should skip malformed line
    
    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Write mixed entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "geofence_exit", "message": "test1"})
        self.logger.log_system_event("test event")
        self.logger.log_alert({"type": "panic", "message": "test2"})
        
        alerts = self.logger.get_recent_alerts()
        assert len(alerts) == 2
        assert all(alert["event_type"] == "alert" for alert in alerts)
    
    def test_get_recent_locations(self):
        """Test getting recent locations."""
        # Write mixed entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_location(Location(51.5074, -0.1278))
        
        locations = self.logger.get_recent_locations()
        assert len(locations) == 2
        assert all(loc["event_type"] == "location_update" for loc in locations)
    
    def test_get_entries_by_type(self):
        """Test getting entries filtered by type."""
        # Write mixed entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_location(Location(51.5074, -0.1278))
        self.logger.log_alert({"type": "test2", "message": "test2"})
        
        # Get location entries
        locations = self.logger.get_entries_by_type("location_update")
        assert len(locations) == 2
        
        # Get alert entries
        alerts = self.logger.get_entries_by_type("alert")
        assert len(alerts) == 2
    
    def test_get_entries_by_time_range(self):
        """Test getting entries within time range."""
        # Write entries with specific timestamps
        with open(self.log_file_path, 'w') as f:
            f.write('{"timestamp": "2024-01-01T10:00:00", "event_type": "test1"}\n')
            f.write('{"timestamp": "2024-01-01T12:00:00", "event_type": "test2"}\n')
            f.write('{"timestamp": "2024-01-01T14:00:00", "event_type": "test3"}\n')
        
        # Get entries in time range
        entries = self.logger.get_entries_by_time_range(
            "2024-01-01T11:00:00", "2024-01-01T13:00:00"
        )
        assert len(entries) == 1
        assert entries[0]["event_type"] == "test2"
    
    def test_get_statistics_empty_file(self):
        """Test getting statistics from empty file."""
        stats = self.logger.get_statistics()
        
        assert stats["total_entries"] == 0
        assert stats["event_types"] == {}
        assert stats["date_range"]["earliest"] is None
        assert stats["date_range"]["latest"] is None
    
    def test_get_statistics_with_data(self):
        """Test getting statistics with data."""
        # Write entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_location(Location(51.5074, -0.1278))
        
        stats = self.logger.get_statistics()
        
        assert stats["total_entries"] == 3
        assert stats["event_types"]["location_update"] == 2
        assert stats["event_types"]["alert"] == 1
        assert stats["date_range"]["earliest"] is not None
        assert stats["date_range"]["latest"] is not None
    
    def test_clear_log(self):
        """Test clearing the log file."""
        # Write some entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        
        # Verify entries exist
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2
        
        # Clear log
        self.logger.clear_log()
        
        # Verify log is empty
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 0
    
    def test_export_log(self):
        """Test exporting log entries."""
        # Write some entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        
        # Export all entries
        export_path = os.path.join(self.temp_dir, "export.json")
        self.logger.export_log(export_path)
        
        # Verify export file
        assert os.path.exists(export_path)
        with open(export_path, 'r') as f:
            exported = json.load(f)
            assert len(exported) == 2
    
    def test_export_log_filtered(self):
        """Test exporting filtered log entries."""
        # Write mixed entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        self.logger.log_location(Location(51.5074, -0.1278))
        
        # Export only alerts
        export_path = os.path.join(self.temp_dir, "export.json")
        self.logger.export_log(export_path, event_types=["alert"])
        
        # Verify export file
        with open(export_path, 'r') as f:
            exported = json.load(f)
            assert len(exported) == 1
            assert exported[0]["event_type"] == "alert"
    
    def test_concurrent_writes(self):
        """Test concurrent writes to log file."""
        import threading
        import time
        
        def write_entries(thread_id):
            for i in range(10):
                self.logger.log_system_event(f"Thread {thread_id} entry {i}")
                time.sleep(0.001)  # Small delay
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=write_entries, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all entries were written
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 30  # 3 threads * 10 entries each
    
    def test_write_error_handling(self):
        """Test handling of write errors."""
        # Mock file operations to simulate errors
        with patch('builtins.open', side_effect=OSError("Disk full")):
            # Should not raise exception
            self.logger.log_system_event("test event")
    
    def test_read_error_handling(self):
        """Test handling of read errors."""
        # Create a file that can't be read
        with open(self.log_file_path, 'w') as f:
            f.write('{"event_type": "test"}\n')
        
        # Remove read permissions
        os.chmod(self.log_file_path, 0o000)
        
        # Should handle gracefully
        entries = self.logger.get_recent_entries()
        assert entries == []
        
        # Restore permissions for cleanup
        os.chmod(self.log_file_path, 0o644)


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_audit_logger_default(self):
        """Test creating audit logger with default settings."""
        logger = create_audit_logger(self.temp_dir)
        
        assert isinstance(logger, AuditLogger)
        assert logger.log_file_path.name == "audit_log.jsonl"
        assert logger.log_file_path.parent == Path(self.temp_dir)
    
    def test_create_audit_logger_custom_dir(self):
        """Test creating audit logger with custom directory."""
        custom_dir = os.path.join(self.temp_dir, "custom")
        logger = create_audit_logger(custom_dir)
        
        assert logger.log_file_path.parent == Path(custom_dir)
    
    def test_get_logger_statistics(self):
        """Test getting logger statistics."""
        log_file_path = os.path.join(self.temp_dir, "test_stats.jsonl")
        
        # Create logger and write some entries
        logger = AuditLogger(log_file_path)
        logger.log_location(Location(40.7128, -74.0060))
        logger.log_alert({"type": "test", "message": "test"})
        
        # Get statistics
        stats = get_logger_statistics(log_file_path)
        
        assert stats["total_entries"] == 2
        assert "location_update" in stats["event_types"]
        assert "alert" in stats["event_types"]


class TestDataFlowScenarios:
    """Test data flow scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "test_flow.jsonl")
        self.logger = AuditLogger(self.log_file_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_location_data_flow(self):
        """Test complete data flow for location logging."""
        # Input: Location object
        location = Location(40.7128, -74.0060, "2024-01-01T12:00:00")
        
        # Process: Log location
        self.logger.log_location(location)
        
        # Output: Verify JSONL entry
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "location_update"
            assert entry["latitude"] == location.latitude
            assert entry["longitude"] == location.longitude
            assert entry["timestamp"] == location.timestamp
    
    def test_alert_data_flow(self):
        """Test complete data flow for alert logging."""
        # Input: Alert data dictionary
        alert_data = {
            "type": "geofence_exit",
            "message": "Child left safe zone",
            "severity": "high"
        }
        
        # Process: Log alert
        self.logger.log_alert(alert_data)
        
        # Output: Verify JSONL entry
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            entry = json.loads(lines[0])
            assert entry["event_type"] == "alert"
            assert entry["type"] == alert_data["type"]
            assert entry["message"] == alert_data["message"]
            assert entry["severity"] == alert_data["severity"]
    
    def test_multiple_event_types_flow(self):
        """Test data flow with multiple event types."""
        # Input: Various event types
        events = [
            ("location", Location(40.7128, -74.0060)),
            ("alert", {"type": "panic", "message": "Emergency"}),
            ("system", "Simulator started"),
            ("error", "Connection failed")
        ]
        
        # Process: Log all events
        for event_type, data in events:
            if event_type == "location":
                self.logger.log_location(data)
            elif event_type == "alert":
                self.logger.log_alert(data)
            elif event_type == "system":
                self.logger.log_system_event(data)
            elif event_type == "error":
                self.logger.log_error(data)
        
        # Output: Verify all entries
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 4
            
            # Verify each entry type
            entry_types = [json.loads(line)["event_type"] for line in lines]
            assert "location_update" in entry_types
            assert "alert" in entry_types
            assert "system_event" in entry_types
            assert "error" in entry_types
    
    def test_data_recovery_flow(self):
        """Test data recovery flow."""
        # Write some entries
        self.logger.log_location(Location(40.7128, -74.0060))
        self.logger.log_alert({"type": "test", "message": "test"})
        
        # Simulate file corruption (add malformed line)
        with open(self.log_file_path, 'a') as f:
            f.write("malformed json line\n")
        
        # Write more entries
        self.logger.log_location(Location(51.5074, -0.1278))
        
        # Recovery: Read entries (should skip malformed line)
        entries = self.logger.get_recent_entries()
        assert len(entries) == 3  # Should have 3 valid entries
        
        # Verify data integrity
        valid_entries = [e for e in entries if e.get("event_type")]
        assert len(valid_entries) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 