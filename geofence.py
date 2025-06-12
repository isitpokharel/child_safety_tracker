"""
Geofence Module - Distance math & boundary checks
Author: Isit Pokharel
Purpose: Pure-Python geometry check for circular safe zones
"""

import math
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class Location:
    """Represents a GPS location with latitude and longitude."""
    latitude: float
    longitude: float
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Validate latitude and longitude ranges."""
        if self.latitude is None:
            raise ValueError("Latitude cannot be None")
        if self.longitude is None:
            raise ValueError("Longitude cannot be None")
            
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
            
        # Validate timestamp format if provided
        if self.timestamp is not None:
            try:
                # Try parsing the timestamp to ensure it's valid
                from datetime import datetime
                datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {self.timestamp}")


@dataclass
class Geofence:
    """Represents a circular geofence with center and radius."""
    center: Location
    radius_meters: float

    def __post_init__(self):
        """Validate radius is positive."""
        if self.radius_meters <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius_meters}")


class GeofenceChecker:
    """Handles geofence boundary calculations and checks."""
    
    # Earth's radius in meters (approximate)
    EARTH_RADIUS = 6371000
    
    @staticmethod
    def haversine_distance(loc1: Location, loc2: Location) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        
        Args:
            loc1: First location
            loc2: Second location
            
        Returns:
            Distance in meters
            
        Raises:
            ValueError: If locations are invalid
        """
        if not isinstance(loc1, Location) or not isinstance(loc2, Location):
            raise ValueError("Both arguments must be Location objects")
        
        # Convert to radians
        lat1_rad = math.radians(loc1.latitude)
        lon1_rad = math.radians(loc1.longitude)
        lat2_rad = math.radians(loc2.latitude)
        lon2_rad = math.radians(loc2.longitude)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        
        return GeofenceChecker.EARTH_RADIUS * c
    
    @staticmethod
    def is_inside_geofence(location: Location, geofence: Geofence) -> bool:
        """
        Check if a location is inside a geofence.
        
        Args:
            location: Location to check
            geofence: Geofence to check against
            
        Returns:
            True if location is inside geofence, False otherwise
            
        Raises:
            ValueError: If arguments are invalid
        """
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        if not isinstance(geofence, Geofence):
            raise ValueError("geofence must be a Geofence object")
        
        distance = GeofenceChecker.haversine_distance(location, geofence.center)
        return distance <= geofence.radius_meters
    
    @staticmethod
    def distance_to_geofence_boundary(location: Location, geofence: Geofence) -> float:
        """
        Calculate the distance from a location to the geofence boundary.
        Positive values mean outside, negative values mean inside.
        
        Args:
            location: Location to check
            geofence: Geofence to check against
            
        Returns:
            Distance in meters (positive = outside, negative = inside)
        """
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        if not isinstance(geofence, Geofence):
            raise ValueError("geofence must be a Geofence object")
        
        distance_to_center = GeofenceChecker.haversine_distance(location, geofence.center)
        return distance_to_center - geofence.radius_meters
    
    @staticmethod
    def create_default_geofence(center_lat: float, center_lon: float, 
                               radius_meters: float = 1000) -> Geofence:
        """
        Create a default geofence with specified center and radius.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_meters: Radius in meters (default: 1000m)
            
        Returns:
            Geofence object
        """
        center = Location(center_lat, center_lon)
        return Geofence(center, radius_meters)


# Convenience functions for common operations
def check_location_safety(location: Location, geofence: Geofence) -> Tuple[bool, float]:
    """
    Check if a location is safe (inside geofence) and return distance to boundary.
    
    Args:
        location: Location to check
        geofence: Geofence to check against
        
    Returns:
        Tuple of (is_safe, distance_to_boundary)
    """
    is_safe = GeofenceChecker.is_inside_geofence(location, geofence)
    distance = GeofenceChecker.distance_to_geofence_boundary(location, geofence)
    return is_safe, distance


def create_home_geofence(home_lat: float, home_lon: float) -> Geofence:
    """
    Create a home geofence with 1km radius.
    
    Args:
        home_lat: Home latitude
        home_lon: Home longitude
        
    Returns:
        Geofence object with 1km radius
    """
    return GeofenceChecker.create_default_geofence(home_lat, home_lon, 1000) 