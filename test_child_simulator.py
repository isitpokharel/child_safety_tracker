"""
Unit Tests for Child Simulator Module
Author: KiddoTrack-Lite Team
Purpose: Child device simulation and UI testing
"""

import pytest
import asyncio
import signal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import httpx
from rich.console import Console
from rich.panel import Panel

from child_simulator import ChildSimulator
from geofence import Location, Geofence
from simulator import EmergencyState, GPSSimulator, SimulatorConfig


class TestChildSimulator:
    """Test cases for ChildSimulator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            self.child_simulator = ChildSimulator()
    
    def test_initialization(self):
        """Test child simulator initialization."""
        with patch('child_simulator.GPSSimulator') as mock_gps_sim, \
             patch('child_simulator.signal.signal') as mock_signal:
            
            # Mock GPS simulator
            mock_simulator = Mock()
            mock_gps_sim.return_value = mock_simulator
            
            child_sim = ChildSimulator()
            
            assert child_sim.api_url == "http://localhost:8000"
            assert isinstance(child_sim.console, Console)
            assert child_sim.simulator == mock_simulator
            assert child_sim.current_location is None
            assert child_sim.geofence is None
            assert child_sim.emergency_state == EmergencyState.NORMAL
            assert child_sim.is_running is False
            assert child_sim.last_alert_time == 0
            
            # Verify signal handlers were set up
            assert mock_signal.call_count == 2
    
    def test_initialization_with_custom_api_url(self):
        """Test child simulator initialization with custom API URL."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator(api_url="http://custom:9000")
            assert child_sim.api_url == "http://custom:9000"
    
    def test_signal_handler(self):
        """Test signal handler functionality."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.is_running = True
            
            with patch.object(child_sim.console, 'print') as mock_print:
                # Simulate SIGINT
                child_sim._signal_handler(signal.SIGINT, None)
                
                assert child_sim.is_running is False
                mock_print.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Test successful status update."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "current_location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timestamp": "2024-01-01T12:00:00"
                },
                "emergency_state": "normal",
                "geofence_active": True
            }
            
            with patch.object(child_sim.client, 'get', return_value=mock_response) as mock_get, \
                 patch.object(child_sim, '_update_geofence') as mock_update_geofence:
                
                await child_sim._update_data()
                
                mock_get.assert_called_once_with(f"{child_sim.api_url}/status")
                mock_update_geofence.assert_called_once()
                
                # Verify location was updated
                assert child_sim.current_location is not None
                assert child_sim.current_location.latitude == 40.7128
                assert child_sim.current_location.longitude == -74.0060
                assert child_sim.emergency_state == EmergencyState.NORMAL
    
    @pytest.mark.asyncio
    async def test_update_geofence_success(self):
        """Test successful geofence update."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "center": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                },
                "radius_meters": 1000.0
            }
            
            with patch.object(child_sim.client, 'get', return_value=mock_response) as mock_get:
                await child_sim._update_geofence()
                
                mock_get.assert_called_once_with(f"{child_sim.api_url}/geofence")
                
                # Verify geofence was updated
                assert child_sim.geofence is not None
                assert child_sim.geofence.center.latitude == 40.7128
                assert child_sim.geofence.center.longitude == -74.0060
                assert child_sim.geofence.radius_meters == 1000.0
    
    @pytest.mark.asyncio
    async def test_update_geofence_failure(self):
        """Test geofence update failure handling."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.client, 'get', side_effect=Exception("Network error")):
                # Should not raise exception
                await child_sim._update_geofence()
                
                # Geofence should remain None
                assert child_sim.geofence is None
    
    @pytest.mark.asyncio
    async def test_update_data_error_handling(self):
        """Test update data error handling."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.client, 'get', side_effect=Exception("Network error")), \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim._update_data()
                
                # Should print error message
                mock_print.assert_called()
                assert "Error updating data" in str(mock_print.call_args)
    
    def test_on_location_update_no_geofence(self):
        """Test location update callback without geofence."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = None
            
            location = Location(40.7128, -74.0060)
            
            # Should not raise exception
            child_sim._on_location_update(location)
            
            assert child_sim.current_location == location
    
    def test_on_location_update_with_geofence_safe(self):
        """Test location update callback with geofence - safe location."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            
            location = Location(40.7128, -74.0060)  # Same as center
            
            with patch('child_simulator.check_location_safety', return_value=(True, 0.0)):
                child_sim._on_location_update(location)
                
                assert child_sim.current_location == location
    
    def test_on_location_update_with_geofence_unsafe(self):
        """Test location update callback with geofence - unsafe location."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            child_sim.last_alert_time = 0  # Allow alert
            
            location = Location(40.8000, -74.0060)  # Far from center
            
            with patch('child_simulator.check_location_safety', return_value=(False, 2000.0)), \
                 patch('child_simulator.time.time', return_value=100), \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                child_sim._on_location_update(location)
                
                assert child_sim.current_location == location
                mock_print.assert_called_once()
                assert "Left safe zone" in str(mock_print.call_args)
    
    def test_on_location_update_alert_cooldown(self):
        """Test location update alert cooldown functionality."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            child_sim.last_alert_time = 90  # Recent alert
            
            location = Location(40.8000, -74.0060)  # Far from center
            
            with patch('child_simulator.check_location_safety', return_value=(False, 2000.0)), \
                 patch('child_simulator.time.time', return_value=100), \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                child_sim._on_location_update(location)
                
                # Should not print alert due to cooldown
                mock_print.assert_not_called()
    
    def test_on_emergency_update_panic(self):
        """Test emergency update callback - panic state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.console, 'print') as mock_print:
                child_sim._on_emergency_update(EmergencyState.PANIC)
                
                assert child_sim.emergency_state == EmergencyState.PANIC
                mock_print.assert_called_once()
                assert "PANIC TRIGGERED" in str(mock_print.call_args)
    
    def test_on_emergency_update_resolved(self):
        """Test emergency update callback - resolved state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.console, 'print') as mock_print:
                child_sim._on_emergency_update(EmergencyState.RESOLVED)
                
                assert child_sim.emergency_state == EmergencyState.RESOLVED
                mock_print.assert_called_once()
                assert "Panic resolved" in str(mock_print.call_args)
    
    def test_on_emergency_update_normal(self):
        """Test emergency update callback - normal state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.console, 'print') as mock_print:
                child_sim._on_emergency_update(EmergencyState.NORMAL)
                
                assert child_sim.emergency_state == EmergencyState.NORMAL
                mock_print.assert_called_once()
                assert "Back to normal" in str(mock_print.call_args)
    
    @pytest.mark.asyncio
    async def test_trigger_panic_success(self):
        """Test successful panic trigger."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            
            with patch.object(child_sim.client, 'post', return_value=mock_response) as mock_post, \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim.trigger_panic()
                
                mock_post.assert_called_once_with(f"{child_sim.api_url}/panic")
                mock_print.assert_called_once()
                assert "Manual panic triggered" in str(mock_print.call_args)
    
    @pytest.mark.asyncio
    async def test_trigger_panic_failure(self):
        """Test panic trigger failure."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response - failure
            mock_response = Mock()
            mock_response.status_code = 500
            
            with patch.object(child_sim.client, 'post', return_value=mock_response) as mock_post, \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim.trigger_panic()
                
                mock_post.assert_called_once_with(f"{child_sim.api_url}/panic")
                mock_print.assert_called_once()
                assert "Failed to trigger panic" in str(mock_print.call_args)
    
    @pytest.mark.asyncio
    async def test_trigger_panic_exception(self):
        """Test panic trigger exception handling."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            with patch.object(child_sim.client, 'post', side_effect=Exception("Network error")), \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim.trigger_panic()
                
                mock_print.assert_called_once()
                assert "Error triggering panic" in str(mock_print.call_args)
    
    @pytest.mark.asyncio
    async def test_resolve_panic_success(self):
        """Test successful panic resolution."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            
            with patch.object(child_sim.client, 'post', return_value=mock_response) as mock_post, \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim.resolve_panic()
                
                mock_post.assert_called_once_with(f"{child_sim.api_url}/panic/resolve")
                mock_print.assert_called_once()
                assert "Manual panic resolution" in str(mock_print.call_args)
    
    @pytest.mark.asyncio
    async def test_resolve_panic_failure(self):
        """Test panic resolution failure."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock HTTP response - failure
            mock_response = Mock()
            mock_response.status_code = 500
            
            with patch.object(child_sim.client, 'post', return_value=mock_response) as mock_post, \
                 patch.object(child_sim.console, 'print') as mock_print:
                
                await child_sim.resolve_panic()
                
                mock_post.assert_called_once_with(f"{child_sim.api_url}/panic/resolve")
                mock_print.assert_called_once()
                assert "Failed to resolve panic" in str(mock_print.call_args)
    
    def test_create_header_normal_state(self):
        """Test header creation in normal state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.emergency_state = EmergencyState.NORMAL
            
            panel = child_sim._create_header()
            
            assert isinstance(panel, Panel)
            assert "Normal Operation" in str(panel) or "Normal" in str(panel)
    
    def test_create_header_panic_state(self):
        """Test header creation in panic state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.emergency_state = EmergencyState.PANIC
            
            panel = child_sim._create_header()
            
            assert isinstance(panel, Panel)
            assert "EMERGENCY" in str(panel) or "PANIC" in str(panel)
    
    def test_create_header_resolved_state(self):
        """Test header creation in resolved state."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.emergency_state = EmergencyState.RESOLVED
            
            panel = child_sim._create_header()
            
            assert isinstance(panel, Panel)
            assert "Emergency Resolved" in str(panel) or "Resolved" in str(panel)
    
    def test_create_location_no_location(self):
        """Test location panel creation with no location data."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.current_location = None
            
            panel = child_sim._create_location()
            
            assert isinstance(panel, Panel)
            assert "No location data available" in str(panel)
    
    def test_create_location_with_location(self):
        """Test location panel creation with location data."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.current_location = Location(40.7128, -74.0060, "2024-01-01T12:00:00")
            child_sim.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            
            with patch('child_simulator.check_location_safety', return_value=(True, 0.0)):
                panel = child_sim._create_location()
                
                assert isinstance(panel, Panel)
                # Should contain location coordinates
                assert "40.7128" in str(panel)
                assert "-74.0060" in str(panel)
    
    def test_create_status(self):
        """Test status panel creation."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock simulator properties
            mock_simulator = Mock()
            mock_simulator._running = True
            mock_simulator.config.update_frequency = 1.0
            child_sim.simulator = mock_simulator
            child_sim.emergency_state = EmergencyState.NORMAL
            child_sim.is_running = True
            
            panel = child_sim._create_status()
            
            assert isinstance(panel, Panel)
            assert "Device Status" in str(panel)
    
    def test_create_controls(self):
        """Test controls panel creation."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            # Mock simulator properties
            mock_simulator = Mock()
            mock_simulator._running = True
            child_sim.simulator = mock_simulator
            child_sim.emergency_state = EmergencyState.NORMAL
            
            panel = child_sim._create_controls()
            
            assert isinstance(panel, Panel)
            assert "Controls" in str(panel)
            assert "Ctrl+C" in str(panel)
    
    def test_create_info(self):
        """Test info panel creation."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            
            panel = child_sim._create_info()
            
            assert isinstance(panel, Panel)
            assert "Device Info" in str(panel)
            assert "Child Simulator" in str(panel)
    
    def test_create_info_no_geofence(self):
        """Test info panel creation without geofence."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            child_sim.geofence = None
            
            panel = child_sim._create_info()
            
            assert isinstance(panel, Panel)
            assert "Not set" in str(panel)
    
    def test_create_footer(self):
        """Test footer panel creation."""
        with patch('child_simulator.GPSSimulator'), \
             patch('child_simulator.signal.signal'):
            child_sim = ChildSimulator()
            
            panel = child_sim._create_footer()
            
            assert isinstance(panel, Panel)
            assert "KiddoTrack-Lite" in str(panel)
            assert "CISC 593" in str(panel)


class TestChildSimulatorIntegration:
    """Integration test cases for ChildSimulator."""
    
    @pytest.mark.asyncio
    async def test_full_update_cycle(self):
        """Test a complete update cycle."""
        with patch('child_simulator.GPSSimulator') as mock_gps_sim, \
             patch('child_simulator.signal.signal'):
            
            # Mock GPS simulator
            mock_simulator = Mock()
            mock_gps_sim.return_value = mock_simulator
            
            child_sim = ChildSimulator()
            
            # Mock all HTTP responses
            status_response = Mock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "current_location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timestamp": "2024-01-01T12:00:00"
                },
                "emergency_state": "normal",
                "geofence_active": True
            }
            
            geofence_response = Mock()
            geofence_response.status_code = 200
            geofence_response.json.return_value = {
                "center": {"latitude": 40.7128, "longitude": -74.0060},
                "radius_meters": 1000.0
            }
            
            with patch.object(child_sim.client, 'get') as mock_get:
                mock_get.side_effect = [status_response, geofence_response]
                
                await child_sim._update_data()
                
                # Verify all data was updated
                assert child_sim.current_location is not None
                assert child_sim.geofence is not None
                assert child_sim.emergency_state == EmergencyState.NORMAL
    
    def test_callback_integration(self):
        """Test integration of location and emergency callbacks."""
        with patch('child_simulator.GPSSimulator') as mock_gps_sim, \
             patch('child_simulator.signal.signal'):
            
            # Mock GPS simulator
            mock_simulator = Mock()
            mock_gps_sim.return_value = mock_simulator
            
            child_sim = ChildSimulator()
            
            # Verify callbacks were added to simulator
            mock_simulator.add_location_callback.assert_called_once()
            mock_simulator.add_emergency_callback.assert_called_once()
            
            # Get the callback functions
            location_callback = mock_simulator.add_location_callback.call_args[0][0]
            emergency_callback = mock_simulator.add_emergency_callback.call_args[0][0]
            
            # Test location callback
            test_location = Location(40.7128, -74.0060)
            location_callback(test_location)
            assert child_sim.current_location == test_location
            
            # Test emergency callback
            emergency_callback(EmergencyState.PANIC)
            assert child_sim.emergency_state == EmergencyState.PANIC


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 