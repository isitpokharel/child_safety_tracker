"""
Test module for audit logger
Author: Bhushan Chandrakant
Purpose: Test audit logging functionality
"""

import os
import json
import time
from datetime import datetime
from unittest import TestCase
import pytest
from logger import AuditLogger, create_logger


class TestAuditLogger(TestCase):
    """Test audit logger functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_file = f"test_audit_{int(time.time())}.log"
        self.logger = AuditLogger(self.test_file)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
    
    def test_log_event(self):
        """Test logging an event."""
        event_type = "test_event"
        details = {"key": "value"}
        self.logger.log_event(event_type, details)
        
        entries = self.logger.get_recent_entries(1)
        assert len(entries) == 1
        assert entries[0].event_type == event_type
        assert entries[0].details == details
    
    def test_get_recent_entries(self):
        """Test getting recent entries."""
        for i in range(5):
            self.logger.log_event("test", {"index": i})
        
        entries = self.logger.get_recent_entries(3)
        assert len(entries) == 3
        assert entries[-1].details["index"] == 4
    
    def test_get_statistics(self):
        """Test getting statistics."""
        self.logger.log_event("location_update", {"lat": 0, "lon": 0})
        self.logger.log_event("panic", {"reason": "test"})
        self.logger.log_event("geofence_violation", {"distance": 100})
        self.logger.log_event("error", {"message": "test error"})
        
        stats = self.logger.get_statistics()
        assert stats["total_entries"] == 4
        assert stats["location_updates"] == 1
        assert stats["panic_events"] == 1
        assert stats["geofence_violations"] == 1
        assert stats["errors"] == 1
    
    def test_clear(self):
        """Test clearing log."""
        self.logger.log_event("test", {"data": "test"})
        self.logger.clear()
        
        entries = self.logger.get_recent_entries()
        assert len(entries) == 0
        
        stats = self.logger.get_statistics()
        assert stats["total_entries"] == 0
    
    def test_file_persistence(self):
        """Test log file persistence."""
        event_data = {"test": "data"}
        self.logger.log_event("test", event_data)
        
        # Read file directly
        with open(self.test_file, "r") as f:
            line = f.readline().strip()
            entry = json.loads(line)
            assert entry["event_type"] == "test"
            assert entry["details"] == event_data
    
    def test_concurrent_logging(self):
        """Test concurrent logging."""
        import threading
        
        def log_events():
            for i in range(100):
                self.logger.log_event("test", {"thread": i})
        
        threads = [threading.Thread(target=log_events) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        entries = self.logger.get_recent_entries(1000)
        assert len(entries) == 300
    
    def test_invalid_event_type(self):
        """Test logging with invalid event type."""
        with pytest.raises(ValueError):
            self.logger.log_event(None, {})
    
    def test_invalid_details(self):
        """Test logging with invalid details."""
        with pytest.raises(ValueError):
            self.logger.log_event("test", None)
    
    def test_file_error_handling(self):
        """Test file error handling."""
        # Make log file read-only
        self.logger.log_event("test", {"data": "test"})
        os.chmod(self.test_file, 0o444)
        
        # Should not raise exception
        self.logger.log_event("test", {"data": "test"})
    
    def test_create_logger(self):
        """Test logger creation."""
        logger = create_logger()
        assert isinstance(logger, AuditLogger)
        assert logger.log_file.startswith("audit_")
        assert logger.log_file.endswith(".log")
        
        # Clean up
        if os.path.exists(logger.log_file):
            os.remove(logger.log_file) 