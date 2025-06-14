"""
Geofence Module
Author: Isit Pokharel
Purpose: Geofence calculations and location validation
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Location:
    """Location data structure."""
    latitude: float
    longitude: float
    timestamp: str = None
    
    def __post_init__(self):
        """Validate location coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")


@dataclass
class Geofence:
    """Geofence data structure."""
    center: Location
    radius_meters: float
    
    def __post_init__(self):
        """Validate geofence parameters."""
        if self.radius_meters <= 0:
            raise ValueError("Radius must be positive")


class GeofenceChecker:
    """Geofence checking functionality."""
    
    EARTH_RADIUS = 6371000  # Earth's radius in meters
    
    @classmethod
    def haversine_distance(cls, location1: Location, location2: Location) -> float:
        """
        Calculate the great circle distance between two points using the haversine formula.
        
        Args:
            location1: First location
            location2: Second location
            
        Returns:
            Distance in meters
        """
        if not isinstance(location1, Location) or not isinstance(location2, Location):
            raise ValueError("Both arguments must be Location objects")
        
        lat1 = math.radians(location1.latitude)
        lon1 = math.radians(location1.longitude)
        lat2 = math.radians(location2.latitude)
        lon2 = math.radians(location2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return cls.EARTH_RADIUS * c
    
    @classmethod
    def is_inside_geofence(cls, location: Location, geofence: Geofence) -> bool:
        """
        Check if a location is inside a geofence.
        
        Args:
            location: Location to check
            geofence: Geofence to check against
            
        Returns:
            True if location is inside geofence, False otherwise
        """
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        if not isinstance(geofence, Geofence):
            raise ValueError("geofence must be a Geofence object")
        
        distance = cls.haversine_distance(location, geofence.center)
        return distance <= geofence.radius_meters
    
    @classmethod
    def distance_to_geofence_boundary(cls, location: Location, geofence: Geofence) -> float:
        """
        Calculate distance from location to geofence boundary.
        
        Args:
            location: Location to check
            geofence: Geofence to check against
            
        Returns:
            Distance to boundary in meters (negative if inside)
        """
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        if not isinstance(geofence, Geofence):
            raise ValueError("geofence must be a Geofence object")
        
        distance = cls.haversine_distance(location, geofence.center)
        return distance - geofence.radius_meters
    
    @classmethod
    def create_default_geofence(cls, latitude: float, longitude: float, radius: float = 1000.0) -> Geofence:
        """
        Create a default geofence at specified location.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in meters
            
        Returns:
            Geofence object
        """
        center = Location(latitude=latitude, longitude=longitude)
        return Geofence(center=center, radius_meters=radius)


def check_location_safety(location: Location, geofence: Geofence) -> Tuple[bool, float]:
    """
    Check if a location is safe (inside geofence) and get distance to center.
    
    Args:
        location: Location to check
        geofence: Geofence to check against
        
    Returns:
        Tuple of (is_safe, distance_to_boundary)
    """
    if not isinstance(location, Location):
        raise ValueError("location must be a Location object")
    if not isinstance(geofence, Geofence):
        raise ValueError("geofence must be a Geofence object")
    
    distance = GeofenceChecker.haversine_distance(location, geofence.center)
    is_safe = distance <= geofence.radius_meters
    
    return is_safe, GeofenceChecker.distance_to_geofence_boundary(location, geofence)


def create_home_geofence(latitude: float, longitude: float, radius: float = 1000.0) -> Geofence:
    """
    Create a geofence centered at home location.
    
    Args:
        latitude: Home latitude
        longitude: Home longitude
        radius: Geofence radius in meters (default: 1000m)
        
    Returns:
        Geofence object
    """
    center = Location(latitude=latitude, longitude=longitude)
    return Geofence(center=center, radius_meters=radius) 