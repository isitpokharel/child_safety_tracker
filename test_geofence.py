"""
Unit Tests for Geofence Module
Author: Isit Pokharel
Purpose: Equivalence partitioning + boundary value testing for geofence calculations
"""

import pytest
import math
from geofence import Location, Geofence, GeofenceChecker, check_location_safety, create_home_geofence


class TestLocation:
    """Test cases for Location class."""
    
    def test_valid_location_creation(self):
        """Test creating valid locations."""
        # Valid coordinates
        loc1 = Location(40.7128, -74.0060)
        assert loc1.latitude == 40.7128
        assert loc1.longitude == -74.0060
        assert loc1.timestamp is None
        
        loc2 = Location(0.0, 0.0, "2024-01-01 12:00:00")
        assert loc2.latitude == 0.0
        assert loc2.longitude == 0.0
        assert loc2.timestamp == "2024-01-01 12:00:00"
    
    def test_invalid_latitude_boundary_values(self):
        """Test boundary value analysis for latitude."""
        # Boundary values: -90, -89.9, 89.9, 90
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            Location(-90.1, 0.0)
        
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            Location(90.1, 0.0)
        
        # Valid boundary values
        Location(-90.0, 0.0)  # Should not raise
        Location(90.0, 0.0)   # Should not raise
        Location(-89.9, 0.0)  # Should not raise
        Location(89.9, 0.0)   # Should not raise
    
    def test_invalid_longitude_boundary_values(self):
        """Test boundary value analysis for longitude."""
        # Boundary values: -180, -179.9, 179.9, 180
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            Location(0.0, -180.1)
        
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            Location(0.0, 180.1)
        
        # Valid boundary values
        Location(0.0, -180.0)  # Should not raise
        Location(0.0, 180.0)   # Should not raise
        Location(0.0, -179.9)  # Should not raise
        Location(0.0, 179.9)   # Should not raise
    
    def test_equivalence_partitioning_latitude(self):
        """Test equivalence partitioning for latitude."""
        # Valid partitions: [-90, 90]
        # Invalid partitions: < -90, > 90
        
        # Valid partition tests
        valid_lats = [-90, -45, 0, 45, 90]
        for lat in valid_lats:
            Location(lat, 0.0)  # Should not raise
        
        # Invalid partition tests
        invalid_lats = [-91, -90.1, 90.1, 91]
        for lat in invalid_lats:
            with pytest.raises(ValueError):
                Location(lat, 0.0)
    
    def test_equivalence_partitioning_longitude(self):
        """Test equivalence partitioning for longitude."""
        # Valid partitions: [-180, 180]
        # Invalid partitions: < -180, > 180
        
        # Valid partition tests
        valid_lons = [-180, -90, 0, 90, 180]
        for lon in valid_lons:
            Location(0.0, lon)  # Should not raise
        
        # Invalid partition tests
        invalid_lons = [-181, -180.1, 180.1, 181]
        for lon in invalid_lons:
            with pytest.raises(ValueError):
                Location(0.0, lon)


class TestGeofence:
    """Test cases for Geofence class."""
    
    def test_valid_geofence_creation(self):
        """Test creating valid geofences."""
        center = Location(40.7128, -74.0060)
        geofence = Geofence(center, 1000.0)
        
        assert geofence.center == center
        assert geofence.radius_meters == 1000.0
    
    def test_invalid_radius_boundary_values(self):
        """Test boundary value analysis for radius."""
        center = Location(0.0, 0.0)
        
        # Boundary value: 0
        with pytest.raises(ValueError, match="Radius must be positive"):
            Geofence(center, 0.0)
        
        # Boundary value: negative
        with pytest.raises(ValueError, match="Radius must be positive"):
            Geofence(center, -1.0)
        
        # Valid boundary values
        Geofence(center, 0.1)   # Should not raise
        Geofence(center, 1.0)   # Should not raise
        Geofence(center, 1000.0)  # Should not raise
    
    def test_equivalence_partitioning_radius(self):
        """Test equivalence partitioning for radius."""
        center = Location(0.0, 0.0)
        
        # Valid partition: > 0
        valid_radii = [0.1, 1.0, 100.0, 1000.0, 10000.0]
        for radius in valid_radii:
            Geofence(center, radius)  # Should not raise
        
        # Invalid partition: <= 0
        invalid_radii = [0.0, -0.1, -1.0, -100.0]
        for radius in invalid_radii:
            with pytest.raises(ValueError):
                Geofence(center, radius)


class TestGeofenceChecker:
    """Test cases for GeofenceChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.nyc = Location(40.7128, -74.0060)  # New York City
        self.london = Location(51.5074, -0.1278)  # London
        self.tokyo = Location(35.6762, 139.6503)  # Tokyo
        self.sydney = Location(-33.8688, 151.2093)  # Sydney
    
    def test_haversine_distance_same_location(self):
        """Test distance calculation for same location."""
        distance = GeofenceChecker.haversine_distance(self.nyc, self.nyc)
        assert distance == 0.0
    
    def test_haversine_distance_known_distances(self):
        """Test distance calculation with known distances."""
        # NYC to London (approximately 5570 km)
        distance = GeofenceChecker.haversine_distance(self.nyc, self.london)
        assert 5550000 <= distance <= 5590000  # Distance in meters, allow some tolerance
        
        # NYC to Tokyo (approximately 10850 km)
        distance = GeofenceChecker.haversine_distance(self.nyc, self.tokyo)
        assert 10800000 <= distance <= 10900000  # Distance in meters, allow some tolerance
    
    def test_haversine_distance_invalid_inputs(self):
        """Test distance calculation with invalid inputs."""
        with pytest.raises(ValueError, match="Both arguments must be Location objects"):
            GeofenceChecker.haversine_distance("invalid", self.nyc)
        
        with pytest.raises(ValueError, match="Both arguments must be Location objects"):
            GeofenceChecker.haversine_distance(self.nyc, "invalid")
        
        with pytest.raises(ValueError, match="Both arguments must be Location objects"):
            GeofenceChecker.haversine_distance(None, self.nyc)
    
    def test_is_inside_geofence_center(self):
        """Test geofence check at center."""
        geofence = Geofence(self.nyc, 1000.0)
        assert GeofenceChecker.is_inside_geofence(self.nyc, geofence) is True
    
    def test_is_inside_geofence_boundary_values(self):
        """Test geofence check at boundary values."""
        center = Location(0.0, 0.0)
        geofence = Geofence(center, 1000.0)
        
        # Inside boundary (approximately 500m from center)
        # At equator, 1 degree latitude ≈ 111,320 meters
        # So 500m ≈ 500/111320 ≈ 0.0045 degrees
        inside_loc = Location(0.0045, 0.0)  # Approximately 500m north
        assert GeofenceChecker.is_inside_geofence(inside_loc, geofence) is True
        
        # At boundary (approximately 890m from center)
        # 890m ≈ 0.008 degrees (within 1000m boundary)
        boundary_loc = Location(0.008, 0.0)  # Approximately 890m north
        assert GeofenceChecker.is_inside_geofence(boundary_loc, geofence) is True
        
        # Outside boundary (approximately 1500m from center)
        # 1500m ≈ 1500/111320 ≈ 0.0135 degrees
        outside_loc = Location(0.0135, 0.0)  # Approximately 1500m north
        assert GeofenceChecker.is_inside_geofence(outside_loc, geofence) is False
    
    def test_is_inside_geofence_invalid_inputs(self):
        """Test geofence check with invalid inputs."""
        geofence = Geofence(self.nyc, 1000.0)
        
        with pytest.raises(ValueError, match="location must be a Location object"):
            GeofenceChecker.is_inside_geofence("invalid", geofence)
        
        with pytest.raises(ValueError, match="geofence must be a Geofence object"):
            GeofenceChecker.is_inside_geofence(self.nyc, "invalid")
    
    def test_distance_to_geofence_boundary(self):
        """Test distance to geofence boundary calculation."""
        center = Location(0.0, 0.0)
        geofence = Geofence(center, 1000.0)
        
        # Inside geofence
        inside_loc = Location(0.005, 0.0)  # 500m north
        distance = GeofenceChecker.distance_to_geofence_boundary(inside_loc, geofence)
        assert distance < 0  # Negative means inside
        
        # Outside geofence
        outside_loc = Location(0.015, 0.0)  # 1500m north
        distance = GeofenceChecker.distance_to_geofence_boundary(outside_loc, geofence)
        assert distance > 0  # Positive means outside
        
        # At boundary
        boundary_loc = Location(0.009, 0.0)  # 1000m north
        distance = GeofenceChecker.distance_to_geofence_boundary(boundary_loc, geofence)
        assert abs(distance) < 10  # Should be very close to 0
    
    def test_create_default_geofence(self):
        """Test default geofence creation."""
        geofence = GeofenceChecker.create_default_geofence(40.7128, -74.0060, 500.0)
        
        assert geofence.center.latitude == 40.7128
        assert geofence.center.longitude == -74.0060
        assert geofence.radius_meters == 500.0
        
        # Test default radius
        geofence = GeofenceChecker.create_default_geofence(40.7128, -74.0060)
        assert geofence.radius_meters == 1000.0  # Default radius


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_check_location_safety(self):
        """Test check_location_safety function."""
        center = Location(0.0, 0.0)
        geofence = Geofence(center, 1000.0)
        
        # Safe location
        safe_loc = Location(0.005, 0.0)  # 500m north
        is_safe, distance = check_location_safety(safe_loc, geofence)
        assert is_safe is True
        assert distance < 0
        
        # Unsafe location
        unsafe_loc = Location(0.015, 0.0)  # 1500m north
        is_safe, distance = check_location_safety(unsafe_loc, geofence)
        assert is_safe is False
        assert distance > 0
    
    def test_create_home_geofence(self):
        """Test create_home_geofence function."""
        geofence = create_home_geofence(40.7128, -74.0060)
        
        assert geofence.center.latitude == 40.7128
        assert geofence.center.longitude == -74.0060
        assert geofence.radius_meters == 1000.0  # Default home radius


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_extreme_coordinates(self):
        """Test with extreme coordinate values."""
        # Poles
        north_pole = Location(90.0, 0.0)
        south_pole = Location(-90.0, 0.0)
        
        # International date line
        date_line = Location(0.0, 180.0)
        
        # All should be valid
        assert north_pole.latitude == 90.0
        assert south_pole.latitude == -90.0
        assert date_line.longitude == 180.0
    
    def test_very_small_geofence(self):
        """Test with very small geofence radius."""
        center = Location(0.0, 0.0)
        tiny_geofence = Geofence(center, 1.0)  # 1m radius instead of 0.1m
        
        # Location very close to center
        # 0.000001 degrees ≈ 0.11 meters, so use smaller value
        close_loc = Location(0.0000045, 0.0)  # Approximately 0.5m north
        assert GeofenceChecker.is_inside_geofence(close_loc, tiny_geofence) is True
        
        # Location just outside
        far_loc = Location(0.00001, 0.0)  # Approximately 1.1m north
        assert GeofenceChecker.is_inside_geofence(far_loc, tiny_geofence) is False
    
    def test_very_large_geofence(self):
        """Test with very large geofence radius."""
        center = Location(0.0, 0.0)
        huge_geofence = Geofence(center, 10000000.0)  # 10,000km radius
        
        # Location far from center
        far_loc = Location(45.0, 45.0)  # Far away
        assert GeofenceChecker.is_inside_geofence(far_loc, huge_geofence) is True
    
    def test_antipodal_points(self):
        """Test distance calculation for antipodal points."""
        # Points on opposite sides of Earth
        point1 = Location(0.0, 0.0)
        point2 = Location(0.0, 180.0)
        
        distance = GeofenceChecker.haversine_distance(point1, point2)
        # Should be approximately half the Earth's circumference
        expected_distance = math.pi * GeofenceChecker.EARTH_RADIUS
        assert abs(distance - expected_distance) < 100000  # Allow some tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 