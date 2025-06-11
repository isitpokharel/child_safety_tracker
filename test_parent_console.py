"""
Unit Tests for Parent Console Module
Author: KiddoTrack-Lite Team
Purpose: UI functionality and integration testing for parent monitoring console
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import httpx
from rich.console import Console
from rich.panel import Panel

from parent_console import ParentConsole
from geofence import Location, Geofence
from simulator import EmergencyState


class TestParentConsole:
    """Test cases for ParentConsole class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            self.console = ParentConsole()
    
    def test_initialization(self):
        """Test parent console initialization."""
        with patch('parent_console.get_config') as mock_get_config, \
             patch('parent_console.get_ui_config') as mock_get_ui_config:
            
            # Mock config objects
            mock_config = Mock()
            mock_config.get_api_url.return_value = "http://localhost:8000"
            mock_config.api.request_timeout = 30.0
            mock_get_config.return_value = mock_config
            
            mock_ui_config = Mock()
            mock_get_ui_config.return_value = mock_ui_config
            
            console = ParentConsole()
            
            assert console.api_url == "http://localhost:8000"
            assert isinstance(console.console, Console)
            assert console.current_location is None
            assert console.geofence is None
            assert console.emergency_state == EmergencyState.NORMAL
            assert console.recent_alerts == []
            assert console.is_running is False
    
    def test_initialization_with_custom_api_url(self):
        """Test parent console initialization with custom API URL."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole(api_url="http://custom:9000")
            assert console.api_url == "http://custom:9000"
    
    def test_show_welcome(self):
        """Test welcome message display."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            with patch.object(console.console, 'print') as mock_print:
                console._show_welcome()
                mock_print.assert_called_once()
                
                # Check that a Panel was printed
                call_args = mock_print.call_args[0][0]
                assert isinstance(call_args, Panel)
    
    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """Test successful status update."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
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
            
            with patch.object(console.client, 'get', return_value=mock_response) as mock_get, \
                 patch.object(console, '_update_geofence') as mock_update_geofence:
                
                await console._update_status()
                
                mock_get.assert_called_once_with(f"{console.api_url}/status")
                mock_update_geofence.assert_called_once()
                
                # Verify location was updated
                assert console.current_location is not None
                assert console.current_location.latitude == 40.7128
                assert console.current_location.longitude == -74.0060
                assert console.emergency_state == EmergencyState.NORMAL
    
    @pytest.mark.asyncio
    async def test_update_alerts_success(self):
        """Test successful alerts update."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.ui_config.max_recent_alerts = 5
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"type": "geofence_exit", "message": "Child left safe zone"},
                {"type": "panic", "message": "Emergency triggered"}
            ]
            
            with patch.object(console.client, 'get', return_value=mock_response) as mock_get:
                await console._update_alerts()
                
                mock_get.assert_called_once_with(f"{console.api_url}/alerts?limit=5")
                assert len(console.recent_alerts) == 2
                assert console.recent_alerts[0]["type"] == "geofence_exit"
    
    @pytest.mark.asyncio
    async def test_update_geofence_success(self):
        """Test successful geofence update."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
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
            
            with patch.object(console.client, 'get', return_value=mock_response) as mock_get:
                await console._update_geofence()
                
                mock_get.assert_called_once_with(f"{console.api_url}/geofence")
                
                # Verify geofence was updated
                assert console.geofence is not None
                assert console.geofence.center.latitude == 40.7128
                assert console.geofence.center.longitude == -74.0060
                assert console.geofence.radius_meters == 1000.0
    
    @pytest.mark.asyncio
    async def test_update_geofence_failure(self):
        """Test geofence update failure handling."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            with patch.object(console.client, 'get', side_effect=Exception("Network error")):
                # Should not raise exception
                await console._update_geofence()
                
                # Geofence should remain None
                assert console.geofence is None
    
    @pytest.mark.asyncio
    async def test_update_data_timeout_error(self):
        """Test update data timeout error handling."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            with patch.object(console, '_update_status', side_effect=httpx.TimeoutException("Timeout")), \
                 patch.object(console.console, 'print') as mock_print:
                
                await console._update_data()
                
                # Should print timeout error
                mock_print.assert_called_with("[red]API request timeout[/red]")
    
    @pytest.mark.asyncio
    async def test_update_data_connection_error(self):
        """Test update data connection error handling."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            with patch.object(console, '_update_status', side_effect=httpx.ConnectError("Connection failed")), \
                 patch.object(console.console, 'print') as mock_print:
                
                await console._update_data()
                
                # Should print connection error
                mock_print.assert_called_with("[red]Cannot connect to API[/red]")
    
    def test_calculate_child_position(self):
        """Test child position calculation on map."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.ui_config.map_scale_factor = 10000
            
            # Set up test data
            console.current_location = Location(40.7130, -74.0050)  # Slightly offset
            console.geofence = Geofence(
                center=Location(40.7128, -74.0060),  # Center
                radius_meters=1000.0
            )
            
            map_size = 20
            child_x, child_y = console._calculate_child_position(map_size)
            
            # Should return valid coordinates within map bounds
            assert 0 <= child_x < map_size
            assert 0 <= child_y < map_size
    
    def test_draw_geofence_boundary(self):
        """Test geofence boundary drawing."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            map_size = 10
            map_chars = [[" " for _ in range(map_size)] for _ in range(map_size)]
            center_x, center_y = 5, 5
            radius_pixels = 3
            
            console._draw_geofence_boundary(map_chars, center_x, center_y, radius_pixels, map_size)
            
            # Check that some boundary characters were drawn
            boundary_chars = 0
            for row in map_chars:
                for char in row:
                    if char == "·":
                        boundary_chars += 1
            
            assert boundary_chars > 0
    
    def test_create_map_no_location(self):
        """Test map creation when no location data is available."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.current_location = None
            
            panel = console._create_map()
            
            assert isinstance(panel, Panel)
            assert "No location data available" in str(panel)
    
    def test_create_map_with_location_and_geofence(self):
        """Test map creation with location and geofence data."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.ui_config.map_size = 20
            console.ui_config.geofence_display_radius = 8
            console.ui_config.map_scale_factor = 10000
            
            # Set up test data
            console.current_location = Location(40.7128, -74.0060)
            console.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            
            with patch('parent_console.check_location_safety', return_value=(True, 0.0)):
                panel = console._create_map()
                
                assert isinstance(panel, Panel)
                # Should contain map content
                assert "🏠" in str(panel) or "👶" in str(panel) or "Legend" in str(panel)
    
    def test_create_status_no_location(self):
        """Test status panel creation with no location data."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.current_location = None
            console.geofence = None
            
            panel = console._create_status()
            
            assert isinstance(panel, Panel)
            assert "No data" in str(panel)
    
    def test_create_status_with_location(self):
        """Test status panel creation with location data."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.current_location = Location(40.7128, -74.0060, "2024-01-01T12:00:00")
            console.geofence = Geofence(
                center=Location(40.7128, -74.0060),
                radius_meters=1000.0
            )
            console.emergency_state = EmergencyState.NORMAL
            
            with patch('parent_console.check_location_safety', return_value=(True, 0.0)):
                panel = console._create_status()
                
                assert isinstance(panel, Panel)
                # Should contain location coordinates
                assert "40.7128" in str(panel)
                assert "-74.0060" in str(panel)
    
    def test_create_alerts_no_alerts(self):
        """Test alerts panel creation with no alerts."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.recent_alerts = []
            
            panel = console._create_alerts()
            
            assert isinstance(panel, Panel)
            assert "No recent alerts" in str(panel)
    
    def test_create_alerts_with_alerts(self):
        """Test alerts panel creation with alerts."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.recent_alerts = [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "type": "geofence_exit",
                    "message": "Child left safe zone",
                    "severity": "high"
                },
                {
                    "timestamp": "2024-01-01T11:30:00",
                    "type": "panic",
                    "message": "Emergency triggered",
                    "severity": "critical"
                }
            ]
            
            panel = console._create_alerts()
            
            assert isinstance(panel, Panel)
            assert "geofence_exit" in str(panel)
            assert "panic" in str(panel)
    
    def test_create_controls(self):
        """Test controls panel creation."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.is_running = True
            
            panel = console._create_controls()
            
            assert isinstance(panel, Panel)
            assert "Controls" in str(panel)
            assert "Ctrl+C" in str(panel)
    
    def test_create_footer(self):
        """Test footer panel creation."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            
            panel = console._create_footer()
            
            assert isinstance(panel, Panel)
            assert "KiddoTrack-Lite" in str(panel)
            assert "CISC 593" in str(panel)
    
    def test_create_header_normal_state(self):
        """Test header creation in normal state."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.emergency_state = EmergencyState.NORMAL
            
            panel = console._create_header()
            
            assert isinstance(panel, Panel)
            assert "All Systems Normal" in str(panel) or "Normal" in str(panel)
    
    def test_create_header_panic_state(self):
        """Test header creation in panic state."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.emergency_state = EmergencyState.PANIC
            
            panel = console._create_header()
            
            assert isinstance(panel, Panel)
            assert "EMERGENCY" in str(panel) or "PANIC" in str(panel)
    
    def test_create_header_resolved_state(self):
        """Test header creation in resolved state."""
        with patch('parent_console.get_config'), patch('parent_console.get_ui_config'):
            console = ParentConsole()
            console.emergency_state = EmergencyState.RESOLVED
            
            panel = console._create_header()
            
            assert isinstance(panel, Panel)
            assert "Emergency Resolved" in str(panel) or "Resolved" in str(panel)


class TestParentConsoleIntegration:
    """Integration test cases for ParentConsole."""
    
    @pytest.mark.asyncio
    async def test_full_update_cycle(self):
        """Test a complete update cycle."""
        with patch('parent_console.get_config') as mock_get_config, \
             patch('parent_console.get_ui_config') as mock_get_ui_config:
            
            # Mock config objects
            mock_config = Mock()
            mock_config.get_api_url.return_value = "http://localhost:8000"
            mock_config.api.request_timeout = 30.0
            mock_get_config.return_value = mock_config
            
            mock_ui_config = Mock()
            mock_ui_config.max_recent_alerts = 5
            mock_get_ui_config.return_value = mock_ui_config
            
            console = ParentConsole()
            
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
            
            alerts_response = Mock()
            alerts_response.status_code = 200
            alerts_response.json.return_value = [
                {"type": "test", "message": "Test alert"}
            ]
            
            geofence_response = Mock()
            geofence_response.status_code = 200
            geofence_response.json.return_value = {
                "center": {"latitude": 40.7128, "longitude": -74.0060},
                "radius_meters": 1000.0
            }
            
            with patch.object(console.client, 'get') as mock_get:
                mock_get.side_effect = [status_response, alerts_response, geofence_response]
                
                await console._update_data()
                
                # Verify all data was updated
                assert console.current_location is not None
                assert len(console.recent_alerts) == 1
                assert console.geofence is not None
                assert console.emergency_state == EmergencyState.NORMAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 