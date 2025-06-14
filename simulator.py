"""
GPS Simulator Module
Author: Isit Pokharel
Purpose: Simulate GPS location data and manage emergency states
"""

import time
import random
import math
import threading
from typing import Generator, Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from geofence import Location
from datetime import datetime


class EmergencyState(str, Enum):
    """Emergency state enumeration."""
    NORMAL = "normal"
    PANIC = "panic"
    RESOLVED = "resolved"


@dataclass
class SimulatorConfig:
    """Configuration for GPS simulator."""
    home_latitude: float
    home_longitude: float
    update_frequency: float = 1.0  # Hz
    max_wander_distance: float = 2000.0  # meters
    panic_probability: float = 0.01  # 1% chance per update
    
    def __post_init__(self):
        """Validate configuration values."""
        if not -90 <= self.home_latitude <= 90:
            raise ValueError("Home latitude must be between -90 and 90")
        if not -180 <= self.home_longitude <= 180:
            raise ValueError("Home longitude must be between -180 and 180")
        if self.update_frequency <= 0:
            raise ValueError("Update frequency must be positive")
        if self.max_wander_distance <= 0:
            raise ValueError("Maximum wander distance must be positive")
        if not 0 <= self.panic_probability <= 1:
            raise ValueError("Panic probability must be between 0 and 1")


class GPSSimulator:
    """GPS location simulator with emergency state management."""
    
    def __init__(self, config: SimulatorConfig):
        """Initialize simulator with configuration."""
        self.config = config
        self.current_location = Location(
            latitude=config.home_latitude,
            longitude=config.home_longitude,
            timestamp=datetime.utcnow().isoformat()
        )
        self.emergency_state = EmergencyState.NORMAL
        self._running = False
        self._thread = None
        self._state_lock = threading.Lock()
        self._location_callbacks: List[Callable[[Location], None]] = []
        self._emergency_callbacks: List[Callable[[EmergencyState], None]] = []
    
    def add_location_callback(self, callback: Callable[[Location], None]) -> None:
        """Add callback for location updates."""
        self._location_callbacks.append(callback)
    
    def add_emergency_callback(self, callback: Callable[[EmergencyState], None]) -> None:
        """Add callback for emergency state changes."""
        self._emergency_callbacks.append(callback)
    
    def _notify_location_callbacks(self, location: Location) -> None:
        """Notify all location callbacks."""
        for callback in self._location_callbacks:
            try:
                callback(location)
            except Exception as e:
                print(f"Error in location callback: {e}")
    
    def _notify_emergency_callbacks(self, state: EmergencyState) -> None:
        """Notify all emergency callbacks."""
        for callback in self._emergency_callbacks:
            try:
                callback(state)
            except Exception as e:
                print(f"Error in emergency callback: {e}")
    
    def _generate_random_offset(self) -> tuple[float, float]:
        """Generate random offset within max wander distance."""
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, self.config.max_wander_distance)
        lat_offset = distance * math.cos(angle) / 111111.0  # Approximate degrees per meter
        lon_offset = distance * math.sin(angle) / (111111.0 * math.cos(math.radians(self.current_location.latitude)))
        return lat_offset, lon_offset
    
    def _update_location(self) -> None:
        """Update current location with random movement."""
        lat_offset, lon_offset = self._generate_random_offset()
        new_lat = self.current_location.latitude + lat_offset
        new_lon = self.current_location.longitude + lon_offset
        
        # Ensure coordinates stay within valid ranges
        new_lat = max(-90, min(90, new_lat))
        new_lon = max(-180, min(180, new_lon))
        
        self.current_location = Location(
            latitude=new_lat,
            longitude=new_lon,
            timestamp=datetime.utcnow().isoformat()
        )
        self._notify_location_callbacks(self.current_location)
    
    def _check_panic_trigger(self) -> None:
        """Check if panic state should be triggered."""
        if self.emergency_state == EmergencyState.NORMAL:
            if random.random() < self.config.panic_probability:
                self.trigger_panic()
    
    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        while self._running:
            try:
                self._update_location()
                self._check_panic_trigger()
                time.sleep(1.0 / self.config.update_frequency)
            except Exception as e:
                print(f"Error in simulation loop: {e}")
                time.sleep(1.0)  # Prevent tight loop on error
    
    def start(self) -> None:
        """Start the simulator."""
        with self._state_lock:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._simulation_loop)
                self._thread.daemon = True
                self._thread.start()
    
    def stop(self) -> None:
        """Stop the simulator."""
        with self._state_lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
                self._thread = None
    
    def is_running(self) -> bool:
        """Check if simulator is running."""
        with self._state_lock:
            return self._running
    
    def get_current_location(self) -> Location:
        """Get current location."""
        with self._state_lock:
            return self.current_location
    
    def get_emergency_state(self) -> EmergencyState:
        """Get current emergency state."""
        with self._state_lock:
            return self.emergency_state
    
    def set_location(self, location: Location) -> None:
        """Set current location."""
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        
        with self._state_lock:
            self.current_location = location
            self._notify_location_callbacks(location)
    
    def trigger_panic(self) -> None:
        """Trigger panic state."""
        with self._state_lock:
            if self.emergency_state == EmergencyState.NORMAL:
                self.emergency_state = EmergencyState.PANIC
                print("!!! PANIC TRIGGERED !!!")
                self._notify_emergency_callbacks(self.emergency_state)
    
    def resolve_panic(self) -> None:
        """Resolve panic state."""
        with self._state_lock:
            if self.emergency_state == EmergencyState.PANIC:
                self.emergency_state = EmergencyState.RESOLVED
                print("Panic resolved")
                self._notify_emergency_callbacks(self.emergency_state)
    
    def reset_to_normal(self) -> None:
        """Reset emergency state to normal."""
        with self._state_lock:
            if self.emergency_state == EmergencyState.RESOLVED:
                self.emergency_state = EmergencyState.NORMAL
                print("Back to normal state")
                self._notify_emergency_callbacks(self.emergency_state)


class LocationGenerator:
    """Generate location data streams."""
    
    def __init__(self, simulator: GPSSimulator):
        """Initialize with simulator."""
        self.simulator = simulator
        self._locations: List[Location] = []
        self._lock = threading.Lock()
        
        # Add callback to track locations
        simulator.add_location_callback(self._on_location_update)
    
    def _on_location_update(self, location: Location) -> None:
        """Handle location updates."""
        with self._lock:
            self._locations.append(location)
            # Keep only last 1000 locations
            if len(self._locations) > 1000:
                self._locations.pop(0)
    
    def generate_locations(self, count: int = 10) -> List[Location]:
        """Generate a stream of locations."""
        with self._lock:
            if not self._locations:
                return []
            return self._locations[-count:]
    
    def get_simulator(self) -> GPSSimulator:
        """Get the underlying simulator."""
        return self.simulator


# Convenience functions
def create_default_simulator(home_lat: float, home_lon: float) -> GPSSimulator:
    """Create a simulator with default settings."""
    config = SimulatorConfig(
        home_latitude=home_lat,
        home_longitude=home_lon
    )
    return GPSSimulator(config)


def create_custom_simulator(
    home_lat: float,
    home_lon: float,
    update_freq: float = 1.0,
    max_wander: float = 2000.0,
    panic_prob: float = 0.01
) -> GPSSimulator:
    """Create a simulator with custom settings."""
    config = SimulatorConfig(
        home_latitude=home_lat,
        home_longitude=home_lon,
        update_frequency=update_freq,
        max_wander_distance=max_wander,
        panic_probability=panic_prob
    )
    return GPSSimulator(config) 