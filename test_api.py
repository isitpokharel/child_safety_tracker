"""
Unit Tests for API Module
Author: Bhushan Chandrakant
Purpose: Happy/negative path + schema validation testing for FastAPI endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from api import app
from geofence import Location, Geofence
from simulator import EmergencyState


class TestAPIModels:
    """Test cases for API Pydantic models."""
    
    def test_location_model_valid(self):
        """Test valid location model creation."""
        from api import LocationModel
        
        # Valid coordinates
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.timestamp is None
        
        # With timestamp
        location = LocationModel(
            latitude=0.0, 
            longitude=0.0, 
            timestamp="2024-01-01T12:00:00"
        )
        assert location.timestamp == "2024-01-01T12:00:00"
    
    def test_location_model_invalid_latitude(self):
        """Test location model with invalid latitude."""
        from api import LocationModel
        
        # Out of range
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            LocationModel(latitude=91.0, longitude=0.0)
        
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            LocationModel(latitude=-91.0, longitude=0.0)
    
    def test_location_model_invalid_longitude(self):
        """Test location model with invalid longitude."""
        from api import LocationModel
        
        # Out of range
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            LocationModel(latitude=0.0, longitude=181.0)
        
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            LocationModel(latitude=0.0, longitude=-181.0)
    
    def test_geofence_model_valid(self):
        """Test valid geofence model creation."""
        from api import GeofenceModel, LocationModel
        
        center = LocationModel(latitude=40.7128, longitude=-74.0060)
        geofence = GeofenceModel(center=center, radius_meters=1000.0)
        
        assert geofence.center == center
        assert geofence.radius_meters == 1000.0
    
    def test_geofence_model_invalid_radius(self):
        """Test geofence model with invalid radius."""
        from api import GeofenceModel, LocationModel
        
        center = LocationModel(latitude=0.0, longitude=0.0)
        
        # Zero radius
        with pytest.raises(ValueError, match="Radius must be positive"):
            GeofenceModel(center=center, radius_meters=0.0)
        
        # Negative radius
        with pytest.raises(ValueError, match="Radius must be positive"):
            GeofenceModel(center=center, radius_meters=-1.0)
    
    def test_alert_model_valid(self):
        """Test valid alert model creation."""
        from api import AlertModel, LocationModel
        
        # Without location
        alert = AlertModel(
            type="geofence_exit",
            message="Child left safe zone",
            severity="high"
        )
        assert alert.type == "geofence_exit"
        assert alert.message == "Child left safe zone"
        assert alert.severity == "high"
        assert alert.location is None
        assert alert.timestamp is not None
        
        # With location
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        alert = AlertModel(
            type="panic",
            message="Emergency triggered",
            location=location,
            severity="critical"
        )
        assert alert.location == location
        assert alert.severity == "critical"
    
    def test_status_model_valid(self):
        """Test valid status model creation."""
        from api import StatusModel, LocationModel
        
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        status = StatusModel(
            is_running=True,
            current_location=location,
            emergency_state="normal",
            geofence_active=True,
            last_update="2024-01-01T12:00:00"
        )
        
        assert status.is_running is True
        assert status.current_location == location
        assert status.emergency_state == "normal"
        assert status.geofence_active is True
        assert status.last_update == "2024-01-01T12:00:00"


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "KiddoTrack-Lite API"
        assert data["version"] == "1.0.0"
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "simulator_initialized" in data
        assert "geofence_configured" in data
        assert "audit_logger_initialized" in data
        assert "active_websocket_connections" in data
    
    @patch('api.simulator')
    @patch('api.geofence')
    def test_get_status_success(self, mock_geofence, mock_simulator):
        """Test successful status retrieval."""
        # Mock simulator
        mock_simulator._running = True
        mock_simulator.get_current_location.return_value = Location(40.7128, -74.0060)
        mock_simulator.get_emergency_state.return_value = EmergencyState.NORMAL
        
        # Mock geofence
        mock_geofence = Mock()
        
        response = self.client.get("/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_running"] is True
        assert data["emergency_state"] == "normal"
        assert data["geofence_active"] is True
        assert "current_location" in data
        assert "last_update" in data
    
    @patch('api.simulator')
    def test_get_status_no_simulator(self, mock_simulator):
        """Test status retrieval when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.get("/status")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.simulator')
    def test_get_location_success(self, mock_simulator):
        """Test successful location retrieval."""
        mock_simulator.get_current_location.return_value = Location(40.7128, -74.0060)
        
        response = self.client.get("/location")
        assert response.status_code == 200
        
        data = response.json()
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060
    
    @patch('api.simulator')
    def test_get_location_no_simulator(self, mock_simulator):
        """Test location retrieval when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.get("/location")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.simulator')
    @patch('api.audit_logger')
    def test_set_location_success(self, mock_audit_logger, mock_simulator):
        """Test successful location setting."""
        mock_simulator.set_location = Mock()
        
        location_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        response = self.client.post("/location", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060
        
        # Verify simulator was called
        mock_simulator.set_location.assert_called_once_with(40.7128, -74.0060)
    
    def test_set_location_invalid_data(self):
        """Test location setting with invalid data."""
        # Invalid latitude
        response = self.client.post("/location", json={
            "latitude": 91.0,
            "longitude": 0.0
        })
        assert response.status_code == 422  # Validation error
        
        # Invalid longitude
        response = self.client.post("/location", json={
            "latitude": 0.0,
            "longitude": 181.0
        })
        assert response.status_code == 422  # Validation error
    
    @patch('api.geofence')
    def test_get_geofence_success(self, mock_geofence):
        """Test successful geofence retrieval."""
        mock_geofence.center = Location(40.7128, -74.0060)
        mock_geofence.radius_meters = 1000.0
        
        response = self.client.get("/geofence")
        assert response.status_code == 200
        
        data = response.json()
        assert data["center"]["latitude"] == 40.7128
        assert data["center"]["longitude"] == -74.0060
        assert data["radius_meters"] == 1000.0
    
    def test_get_geofence_not_configured(self):
        """Test geofence retrieval when not configured."""
        with patch('api.geofence', None):
            response = self.client.get("/geofence")
            assert response.status_code == 404
            assert "No geofence configured" in response.json()["detail"]
    
    @patch('api.geofence')
    @patch('api.audit_logger')
    def test_set_geofence_success(self, mock_audit_logger, mock_geofence):
        """Test successful geofence setting."""
        geofence_data = {
            "center": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "radius_meters": 1000.0
        }
        
        response = self.client.post("/geofence", json=geofence_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["center"]["latitude"] == 40.7128
        assert data["center"]["longitude"] == -74.0060
        assert data["radius_meters"] == 1000.0
    
    def test_set_geofence_invalid_data(self):
        """Test geofence setting with invalid data."""
        # Invalid radius
        response = self.client.post("/geofence", json={
            "center": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "radius_meters": -1.0
        })
        assert response.status_code == 422  # Validation error
    
    @patch('api.simulator')
    @patch('api.audit_logger')
    def test_trigger_panic_success(self, mock_audit_logger, mock_simulator):
        """Test successful panic trigger."""
        mock_simulator.trigger_panic = Mock()
        mock_simulator.get_emergency_state.return_value = EmergencyState.PANIC
        
        response = self.client.post("/panic")
        assert response.status_code == 200
        
        data = response.json()
        assert data["state"] == "panic"
        
        # Verify simulator was called
        mock_simulator.trigger_panic.assert_called_once()
    
    @patch('api.simulator')
    def test_trigger_panic_no_simulator(self, mock_simulator):
        """Test panic trigger when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.post("/panic")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.simulator')
    @patch('api.audit_logger')
    def test_resolve_panic_success(self, mock_audit_logger, mock_simulator):
        """Test successful panic resolution."""
        mock_simulator.resolve_panic = Mock()
        mock_simulator.get_emergency_state.return_value = EmergencyState.RESOLVED
        
        response = self.client.post("/panic/resolve")
        assert response.status_code == 200
        
        data = response.json()
        assert data["state"] == "resolved"
        
        # Verify simulator was called
        mock_simulator.resolve_panic.assert_called_once()
    
    @patch('api.simulator')
    def test_resolve_panic_no_simulator(self, mock_simulator):
        """Test panic resolution when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.post("/panic/resolve")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.simulator')
    def test_start_simulator_success(self, mock_simulator):
        """Test successful simulator start."""
        mock_simulator.start = Mock()
        
        response = self.client.post("/simulator/start")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Simulator started"
        
        # Verify simulator was called
        mock_simulator.start.assert_called_once()
    
    @patch('api.simulator')
    def test_start_simulator_no_simulator(self, mock_simulator):
        """Test simulator start when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.post("/simulator/start")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.simulator')
    def test_stop_simulator_success(self, mock_simulator):
        """Test successful simulator stop."""
        mock_simulator.stop = Mock()
        
        response = self.client.post("/simulator/stop")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Simulator stopped"
        
        # Verify simulator was called
        mock_simulator.stop.assert_called_once()
    
    @patch('api.simulator')
    def test_stop_simulator_no_simulator(self, mock_simulator):
        """Test simulator stop when simulator not initialized."""
        mock_simulator = None
        
        response = self.client.post("/simulator/stop")
        assert response.status_code == 503
        assert "Simulator not initialized" in response.json()["detail"]
    
    @patch('api.audit_logger')
    def test_get_alerts_success(self, mock_audit_logger):
        """Test successful alerts retrieval."""
        mock_alerts = [
            {
                "type": "geofence_exit",
                "message": "Child left safe zone",
                "timestamp": "2024-01-01T12:00:00",
                "severity": "high"
            },
            {
                "type": "panic",
                "message": "Emergency triggered",
                "timestamp": "2024-01-01T12:01:00",
                "severity": "critical"
            }
        ]
        mock_audit_logger.get_recent_alerts.return_value = mock_alerts
        
        response = self.client.get("/alerts?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert data[0]["type"] == "geofence_exit"
        assert data[1]["type"] == "panic"
    
    @patch('api.audit_logger')
    def test_get_alerts_no_logger(self, mock_audit_logger):
        """Test alerts retrieval when logger not initialized."""
        mock_audit_logger = None
        
        response = self.client.get("/alerts")
        assert response.status_code == 503
        assert "Audit logger not initialized" in response.json()["detail"]


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint."""
    
    def test_websocket_connection(self):
        """Test WebSocket connection."""
        with self.client.websocket_connect("/ws") as websocket:
            # Connection should be established
            assert websocket is not None
    
    def test_websocket_disconnect(self):
        """Test WebSocket disconnection."""
        with self.client.websocket_connect("/ws") as websocket:
            # Send a message to keep connection alive
            websocket.send_text("ping")
            
            # Connection should close gracefully
            websocket.close()


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_404_not_found(self):
        """Test 404 error handling."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test method not allowed error."""
        response = self.client.put("/")
        assert response.status_code == 405
    
    def test_invalid_json(self):
        """Test invalid JSON handling."""
        response = self.client.post("/location", data="invalid json")
        assert response.status_code == 422


class TestSchemaValidation:
    """Test schema validation scenarios."""
    
    def test_location_validation_edge_cases(self):
        """Test location validation with edge cases."""
        from api import LocationModel
        
        # Valid edge cases
        LocationModel(latitude=90.0, longitude=180.0)  # Should work
        LocationModel(latitude=-90.0, longitude=-180.0)  # Should work
        
        # Invalid edge cases
        with pytest.raises(ValueError):
            LocationModel(latitude=90.1, longitude=0.0)
        
        with pytest.raises(ValueError):
            LocationModel(latitude=0.0, longitude=180.1)
    
    def test_geofence_validation_edge_cases(self):
        """Test geofence validation with edge cases."""
        from api import GeofenceModel, LocationModel
        
        center = LocationModel(latitude=0.0, longitude=0.0)
        
        # Valid edge cases
        GeofenceModel(center=center, radius_meters=0.1)  # Very small radius
        GeofenceModel(center=center, radius_meters=1000000.0)  # Very large radius
        
        # Invalid edge cases
        with pytest.raises(ValueError):
            GeofenceModel(center=center, radius_meters=0.0)
        
        with pytest.raises(ValueError):
            GeofenceModel(center=center, radius_meters=-0.1)


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    @patch('api.simulator')
    @patch('api.geofence')
    @patch('api.audit_logger')
    def test_complete_workflow(self, mock_audit_logger, mock_geofence, mock_simulator):
        """Test complete API workflow."""
        # Setup mocks
        mock_simulator._running = True
        mock_simulator.get_current_location.return_value = Location(40.7128, -74.0060)
        mock_simulator.get_emergency_state.return_value = EmergencyState.NORMAL
        mock_simulator.trigger_panic = Mock()
        mock_simulator.resolve_panic = Mock()
        
        mock_geofence.center = Location(40.7128, -74.0060)
        mock_geofence.radius_meters = 1000.0
        
        mock_audit_logger.get_recent_alerts.return_value = []
        
        # Test workflow
        # 1. Get status
        response = self.client.get("/status")
        assert response.status_code == 200
        
        # 2. Set location
        response = self.client.post("/location", json={
            "latitude": 40.7128,
            "longitude": -74.0060
        })
        assert response.status_code == 200
        
        # 3. Trigger panic
        response = self.client.post("/panic")
        assert response.status_code == 200
        
        # 4. Resolve panic
        response = self.client.post("/panic/resolve")
        assert response.status_code == 200
        
        # 5. Get alerts
        response = self.client.get("/alerts")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 